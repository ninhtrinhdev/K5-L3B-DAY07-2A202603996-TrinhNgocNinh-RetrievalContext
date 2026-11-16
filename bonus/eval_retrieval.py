"""Run the six retrieval methods on ONE split and report retrieval metrics (answerable questions only).

Hit definition (same for every method): a returned chunk is a hit for a gold item when source_id and page match and
the gold evidence string is contained in the chunk text.
  gold_mode "any"  -> the question is satisfied at cutoff k when ANY gold item is hit in the top-k
  gold_mode "all"  -> (multi-hop) satisfied only when EVERY gold item is hit in the top-k
Reported: Hit@1, Evidence Hit@3, Hit@5 (mode-aware), MRR of the first gold chunk, per-group Hit@3, time, API calls, tokens.
Unanswerable questions are not in the denominators. Run with --split dev while tuning; test only once after freezing.
"""
import argparse
import json
import time
from collections import defaultdict

import common
from retrieval import METHODS, Retriever


def gold_hit(chunk, g):
    return chunk["source_id"] == g["source_id"] and chunk["page"] == g["page"] and g["evidence"] in chunk["text"]


def satisfied(results, q, k):
    top = results[:k]
    hits = [any(gold_hit(c, g) for c in top) for g in q["gold"]]
    return all(hits) if q.get("gold_mode") == "all" else any(hits)


def first_gold_rank(results, q):
    for c in results:
        if any(gold_hit(c, g) for g in q["gold"]):
            return c["rank"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--methods", nargs="*", default=list(METHODS))
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--corpus", default="whs", choices=("whs", "day6"), help="whs = WHO WHS 2023 (bonus); day6 = Day 6 chunks")
    ap.add_argument("--out", default=None, help="default: bonus/results (whs) or results/retrieval-day6 (day6)")
    args = ap.parse_args()
    common.load_env()
    qfile = common.DATA / "questions.json" if args.corpus == "whs" else common.ROOT / "data" / "questions.json"
    questions = [q for q in json.loads(qfile.read_text(encoding="utf-8")) if q["split"] == args.split and q["answerable"]]
    for q in questions:
        q.setdefault("group", q.get("day6_type", "all"))
    out_dir = common.ROOT / (args.out or ("bonus/results" if args.corpus == "whs" else "results/retrieval-day6"))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    with common.connect() as conn:
        retriever = Retriever(conn, args.corpus)
        for method in args.methods:
            fn = getattr(retriever, method)
            traces, errors = [], []
            calls0, pt0, ot0 = common.STATS["api_calls"], common.STATS["prompt_tokens"], common.STATS["output_tokens"]
            started = time.perf_counter()
            for q in questions:
                t0 = time.perf_counter()
                try:
                    results, trace = fn(q["question"], k=args.k)  # only the question text goes in
                except common.ApiError as e:
                    errors.append({"id": q["id"], "error": str(e)[:300]})
                    results, trace = [], {"method": method, "error": str(e)[:300]}
                conn.commit()
                marked = [{"id": c["id"], "rank": c["rank"], "score": round(c["score"], 5), "page": c["page"], "source": c["source"],
                           "kind": c["metadata"]["kind"], "hit": any(gold_hit(c, g) for g in q["gold"]), "text": c["text"][:300]} for c in results]
                traces.append({"query_id": q["id"], "group": q["group"], "split": q["split"], "question": q["question"],
                               "gold_mode": q.get("gold_mode", "any"), "gold": q["gold"], "trace": trace, "results": marked,
                               "hit1": satisfied(results, q, 1), "hit3": satisfied(results, q, 3), "hit5": satisfied(results, q, 5),
                               "first_gold_rank": first_gold_rank(results, q), "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1)})
            n = len(traces)
            by_group = defaultdict(lambda: [0, 0])
            for t in traces:
                by_group[t["group"]][1] += 1
                by_group[t["group"]][0] += int(t["hit3"])
            s = {"method": method, "split": args.split, "n": n,
                 "hit1": f"{sum(t['hit1'] for t in traces)}/{n}", "hit3": f"{sum(t['hit3'] for t in traces)}/{n}",
                 "hit5": f"{sum(t['hit5'] for t in traces)}/{n}",
                 "mrr": round(sum(1 / t["first_gold_rank"] for t in traces if t["first_gold_rank"]) / n, 3),
                 "hit3_by_group": {g: f"{a}/{b}" for g, (a, b) in sorted(by_group.items())},
                 "misses_at_3": [t["query_id"] for t in traces if not t["hit3"]],
                 "errors": errors, "seconds_total": round(time.perf_counter() - started, 1),
                 "ms_per_query": round(sum(t["elapsed_ms"] for t in traces) / n, 1),
                 "api_calls": common.STATS["api_calls"] - calls0,
                 "llm_prompt_tokens": common.STATS["prompt_tokens"] - pt0, "llm_output_tokens": common.STATS["output_tokens"] - ot0}
            summary[method] = s
            (out_dir / f"{args.split}-{method}-traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            # save after every method so a later failure never loses finished results
            path = out_dir / f"{args.split}-summary.json"
            old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            old[method] = s
            path.write_text(json.dumps(old, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(json.dumps(s, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
