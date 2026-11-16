"""Six retrieval methods over the single merged index (text + table + figure chunks).

  dense       query embedding (RETRIEVAL_QUERY) -> pgvector cosine search
  bm25        lexical BM25 over chunk text (in memory, standard library)
  hybrid      dense + bm25 fused with Reciprocal Rank Fusion (rank-based, no score mixing)
  rerank      hybrid top-N candidates -> LLM listwise rerank
  rewrite     query transformation: LLM writes search-oriented rewrites; hybrid for each; RRF over all lists
  multistage  step 1 hybrid; LLM reads the hits and asks follow-up queries for what is still missing; step 2 hybrid; RRF

Every method returns (results, trace): results = ranked chunks with id/text/score/rank/page/source/metadata.
No gold, expected answer or question id is ever passed in here.
"""
import json
import math
import re
import unicodedata
from collections import Counter

import common
from index import cached_embed

import os

# LLM used by rerank / rewrite / multistage. gemini-2.5-flash allows only 20 requests/day on this key's free tier,
# so the default is the lite model; override with RETRIEVAL_LLM and record the value used (it is written to every trace).
LLM = os.environ.get("RETRIEVAL_LLM") or common.default_model()
RRF_K = 60


def tokenize(text):
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", unicodedata.normalize("NFKC", text).casefold())


class Retriever:
    def __init__(self, conn, corpus="whs"):
        """corpus 'whs' = WHO World Health Statistics 2023 in day7_chunks; 'day6' = the Day 6 strategy-B chunks in day6_chunks."""
        self.conn, self.corpus = conn, corpus
        if corpus == "day6":
            rows = conn.execute("SELECT chunk_id, text, source, page, metadata->>'kind', metadata, document_id FROM day6_chunks "
                                "WHERE strategy='B' ORDER BY chunk_id").fetchall()
            self.desc = "WHO guideline 'Recommendations for prevention and treatment of pre-eclampsia and eclampsia' (2011)"
            self._dense_sql = "SELECT chunk_id, 1 - (embedding <=> %s::vector) FROM day6_chunks WHERE strategy='B' ORDER BY embedding <=> %s::vector LIMIT %s"
            self._dense_params = lambda lit, k: (lit, lit, k)
        elif corpus == "whs":
            rows = conn.execute("SELECT chunk_id, text, source, page, kind, metadata, corpus FROM day7_chunks WHERE corpus=%s ORDER BY chunk_id",
                                (common.CORPUS,)).fetchall()
            self.desc = "WHO report 'World health statistics 2023'"
            self._dense_sql = ("SELECT chunk_id, 1 - (embedding <=> %s::vector) FROM day7_chunks WHERE corpus=%s "
                               "ORDER BY embedding <=> %s::vector LIMIT %s")
            self._dense_params = lambda lit, k: (lit, common.CORPUS, lit, k)
        else:
            raise ValueError("corpus phải là 'whs' hoặc 'day6'")
        if not rows:
            raise RuntimeError("bảng chunk trống: chạy bonus/index.py (whs) hoặc nạp Day 6 trước")
        self.chunks = {r[0]: {"id": r[0], "text": r[1], "source_id": r[6], "source": r[2], "page": r[3],
                              "metadata": {**r[5], "kind": r[4] or "text"}} for r in rows}
        self.ids = list(self.chunks)
        self.tf = [Counter(tokenize(self.chunks[i]["text"])) for i in self.ids]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(t for tf in self.tf for t in tf)
        n = len(self.ids)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    # ---------- primitives ----------
    def _pack(self, ranked, method):
        return [{**self.chunks[cid], "score": float(score), "rank": i + 1, "method": method} for i, (cid, score) in enumerate(ranked)]

    def dense(self, query, k=10):
        qv, _ = cached_embed(self.conn, query, "RETRIEVAL_QUERY")
        lit = common.vec_literal(qv)
        rows = self.conn.execute(self._dense_sql, self._dense_params(lit, k)).fetchall()
        return self._pack(rows, "dense"), {"method": "dense", "query": query, "k": k}

    def bm25(self, query, k=10, k1=1.5, b=0.75):
        q = tokenize(query)
        scores = []
        for cid, tf, ln in zip(self.ids, self.tf, self.len):
            s = 0.0
            for t in q:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (k1 + 1) / (f + k1 * (1 - b + b * ln / self.avg))
            if s > 0:
                scores.append((cid, s))
        scores.sort(key=lambda x: (-x[1], x[0]))
        return self._pack(scores[:k], "bm25"), {"method": "bm25", "query": query, "k": k, "k1": k1, "b": b}

    def _rrf(self, lists, k, method):
        agg = Counter()
        for lst in lists:
            for r in lst:
                agg[r["id"]] += 1.0 / (RRF_K + r["rank"])
        ranked = sorted(agg.items(), key=lambda x: (-x[1], x[0]))[:k]
        return self._pack(ranked, method)

    def hybrid(self, query, k=10, depth=30):
        d, _ = self.dense(query, depth)
        l, _ = self.bm25(query, depth)
        return self._rrf([d, l], k, "hybrid"), {"method": "hybrid", "query": query, "k": k, "depth": depth, "fusion": f"RRF k={RRF_K}"}

    # ---------- LLM-assisted methods ----------
    def rerank(self, query, k=10, candidates=15, snippet=1500):
        cand, _ = self.hybrid(query, candidates)
        listing = "\n\n".join(f"[{i}] (page {c['page']}, {c['metadata']['kind']})\n{c['text'][:snippet]}" for i, c in enumerate(cand))
        prompt = (f"Question: {query}\n\nCandidate passages from the {self.desc}:\n\n{listing}\n\n"
                  "Rank the passages by how directly they contain the evidence needed to answer the question "
                  "(the exact table row, figure or sentence). Return JSON: {\"order\": [indices, best first, include every index]}.")
        raw = common.generate(LLM, prompt, json_mode=True, thinking_budget=0, max_tokens=512)
        order = common.parse_order(raw, len(cand))
        seen, final = set(), []
        for i in order + list(range(len(cand))):
            if i not in seen:
                seen.add(i)
                final.append(i)
        ranked = [(cand[i]["id"], 1.0 / (pos + 1)) for pos, i in enumerate(final)][:k]
        return self._pack(ranked, "rerank"), {"method": "rerank", "query": query, "candidates": [c["id"] for c in cand],
                                              "llm": LLM, "llm_order": order, "base": "hybrid"}

    def rewrite(self, query, k=10, n=2):
        prompt = (f"Question about the {self.desc}: {query}\n\n"
                  f"Write {n} alternative search queries that would match the wording of the document: use the terms, "
                  "units, names and years as a table, figure caption or sentence there would print them. "
                  "Do not answer the question and do not invent numbers. Return JSON: {\"queries\": [...]}.")
        raw = common.generate(LLM, prompt, json_mode=True, thinking_budget=0, max_tokens=400)
        try:
            rewrites = [q for q in json.loads(raw)["queries"] if isinstance(q, str) and q.strip()][:n]
        except (ValueError, KeyError, TypeError) as e:
            raise common.ApiError(f"rewrite trả JSON không hợp lệ: {raw[:200]}") from e
        lists = [self.hybrid(q, 30)[0] for q in [query] + rewrites]
        return self._rrf(lists, k, "rewrite"), {"method": "rewrite", "original_query": query, "rewritten_queries": rewrites,
                                                "llm": LLM, "base": "hybrid", "fusion": f"RRF k={RRF_K} over original + rewrites"}

    def multistage(self, query, k=10, first=5, snippet=900, max_followups=2):
        step1, _ = self.hybrid(query, 30)
        listing = "\n\n".join(f"[{c['id']}] (page {c['page']}, {c['metadata']['kind']})\n{c['text'][:snippet]}" for c in step1[:first])
        prompt = (f"Question: {query}\n\nPassages found so far:\n\n{listing}\n\n"
                  "Decide whether these passages already contain ALL the evidence needed. If some part of the question "
                  f"(another country, indicator, year, figure or table) is not covered, write up to {max_followups} short search "
                  "queries for the missing parts only. Do not answer the question. "
                  "Return JSON: {\"covered\": true|false, \"missing\": \"...\", \"followups\": [...]}.")
        raw = common.generate(LLM, prompt, json_mode=True, thinking_budget=0, max_tokens=400)
        try:
            plan = json.loads(raw)
            followups = [q for q in plan.get("followups", []) if isinstance(q, str) and q.strip()][:max_followups]
        except (ValueError, TypeError, AttributeError) as e:
            raise common.ApiError(f"multistage trả JSON không hợp lệ: {raw[:200]}") from e
        lists = [step1] + [self.hybrid(q, 30)[0] for q in followups]
        steps = [{"step": 1, "query": query, "top": [c["id"] for c in step1[:first]]},
                 {"step": 2, "covered": plan.get("covered"), "missing": plan.get("missing"), "followup_queries": followups,
                  "top": [[c["id"] for c in l[:first]] for l in lists[1:]]}]
        return self._rrf(lists, k, "multistage"), {"method": "multistage", "query": query, "steps": steps, "llm": LLM,
                                                   "base": "hybrid", "fusion": f"RRF k={RRF_K} over step 1 + follow-ups"}


METHODS = ("dense", "bm25", "hybrid", "rerank", "rewrite", "multistage")
