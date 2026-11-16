"""Pack real pipeline output into deck/src/data.json and render small figure crops for the deck.

Everything here is copied from bonus/data and bonus/results; nothing is invented. Test questions are NOT exported
(only their counts and hash), so the deck cannot leak held-out gold. Methods without a results file are left out.
Usage: python -X utf8 deck/build_data.py [--pdf path/to/9789240074323-eng.pdf]
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "bonus" / "data"
OUT = ROOT / "deck" / "src" / "data.json"
CROPS = ROOT / "deck" / "public" / "crops"


def load(name, default=None):
    p = D / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


AGENT = ROOT / "results" / "agent"
AGENT_CASES = {"day6": ROOT / "data" / "agent_cases.json", "whs": D / "questions.json"}


def human_review(run_dir, corpus, split):
    """Aggregate the student's manual labels (reviews.json) with the course script. None until every label is filled in."""
    path = run_dir / "reviews.json"
    if not path.exists():
        return None
    import sys
    sys.path.insert(0, str(ROOT / "starter"))
    from agent_metrics import aggregate
    cases = [c for c in json.loads(AGENT_CASES[corpus].read_text(encoding="utf-8")) if c["split"] == split]
    try:
        reviews = json.loads(path.read_text(encoding="utf-8"))
        return aggregate(cases, json.loads((run_dir / "traces.json").read_text(encoding="utf-8")), reviews)
    except (ValueError, TypeError, KeyError):
        return None  # labels incomplete or inconsistent: show "chưa chấm" instead of guessing


def run_summary(run_dir):
    s = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    s.pop("settings", None)
    s["review"] = human_review(run_dir, s["corpus"], s["split"])
    pr = run_dir / "pass_rate.json"
    if pr.exists():  # per-question pass/fail (ADVANCED.md): counts only, no question text
        p = json.loads(pr.read_text(encoding="utf-8"))
        s["pass"] = {"n": p["pass"], "rate": p["rate_percent"], "byGroup": p["by_group"], "needs27": p["needs_27_of_30"]}
    return s


def agent_data(chunk_by_id):
    """Dev traces of the WHO agent (interactive viewer) + summaries of every agent run found on disk. No test question text."""
    out = {"runs": {}, "dev": []}
    for d in sorted(AGENT.glob("*-*-*")) if AGENT.exists() else []:
        if (d / "summary.json").exists():
            out["runs"][d.name] = run_summary(d)
    runs = {}
    for cfg in ("C-dense", "D-hybrid-rerank"):
        d = AGENT / f"whs-dev-{cfg}"
        if (d / "traces.json").exists():
            runs[cfg] = json.loads((d / "traces.json").read_text(encoding="utf-8"))
    if not runs:
        return out
    questions = {q["id"]: q for q in load("questions.json")}
    for qid in [q["id"] for q in questions.values() if q["split"] == "dev"]:
        item = {"id": qid, "group": questions[qid]["group"], "q": questions[qid]["question"], "answerable": questions[qid]["answerable"],
                "expected": questions[qid].get("expected_answer"), "by": {}}
        for cfg, traces in runs.items():
            t = next((x for x in traces if x["query_id"] == qid), None)
            if not t:
                continue
            steps = []
            for e in t["events"]:
                if e["event"] == "search":
                    steps.append({"query": e["query"], "ctx": e["context_ids"],
                                  "res": [{"id": r["id"], "p": r["page"], "k": (r["metadata"] or {}).get("kind", "text")} for r in e["results"]]})
            cites = []
            for cid in t["citations"]:
                c = chunk_by_id.get(cid)
                cites.append({"id": cid, "p": c["page"] if c else None, "k": c["metadata"]["kind"] if c else None,
                              "t": (c["text"][-260:] if c and c["metadata"]["kind"] == "table" else c["text"][:260]) if c else ""})
            end = next((e for e in reversed(t["events"]) if e["event"] in ("abstain", "answer", "search_limit", "invalid_or_missing_citations")), {})
            item["by"][cfg] = {"status": t["status"], "answer": t["answer"], "cites": cites, "steps": steps, "end": end.get("event"),
                               "reason": end.get("reason"), "ms": t["elapsed_ms"], "tokens": t["prompt_tokens"] + t["output_tokens"],
                               "ctxChars": len(t["final_context"]), "goldIn": t["gold_in_final_context"], "error": t.get("error")}
        out["dev"].append(item)
    return out


def test_data():
    """Aggregates of the sealed split once it was run. Question text is never exported."""
    out = {"retrieval": None}
    sp = ROOT / "bonus" / "results" / "test-summary.json"
    if sp.exists():
        s = json.loads(sp.read_text(encoding="utf-8"))
        out["retrieval"] = [{"method": m, "n": v["n"], "hit1": v["hit1"], "hit3": v["hit3"], "hit5": v["hit5"], "mrr": v["mrr"],
                             "byGroup": v["hit3_by_group"], "misses": len(v["misses_at_3"]), "errors": len(v["errors"])} for m, v in s.items()]
    lock = ROOT / "bonus" / "config.lock.json"
    out["lockedRetrieval"] = json.loads(lock.read_text(encoding="utf-8"))["retrieval"]["method"] if lock.exists() else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, default=Path("C:/Users/FPT NGA 8/Dropbox/PC/Downloads/9789240074323-eng.pdf"))
    ap.add_argument("--dpi", type=int, default=84)
    args = ap.parse_args()

    chunks = load("chunks.json")
    figures = load("figures.json")
    desc = load("figure_descriptions.json", {})
    report = load("extract_report.json")
    index_stats = load("index_stats.json", {})
    bench = load("benchmark_report.json")
    questions = load("questions.json")

    # ---- crops (re-rendered small from the PDF; provenance = the WHO report page region) ----
    crops_ok = False
    if args.pdf.exists():
        import pymupdf
        CROPS.mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open(args.pdf)
        for f in figures:
            page = doc[f["page"] - 1]
            page.get_pixmap(dpi=args.dpi, clip=pymupdf.Rect(*f["bbox"])).save(CROPS / f["crop"])
        crops_ok = True

    fig_by_id = {f["id"]: f for f in figures}
    out_chunks = []
    per_page = defaultdict(Counter)
    for c in chunks:
        kind = c["metadata"]["kind"]
        per_page[c["page"]][kind] += 1
        item = {"id": c["id"], "p": c["page"], "k": kind, "n": len(c["text"])}
        if kind == "figure":
            f = fig_by_id[c["id"]]
            item.update({"cap": f["caption"], "crop": f["crop"], "fig": f["figure"],
                         "layer": f["text_in_figure"][len(f["caption"]):].strip()[:260],
                         "desc": desc.get(c["id"], "")[:700], "hasDesc": c["id"] in desc})
        elif kind == "table":
            lines = c["text"].split("\n")
            item.update({"rows": c["metadata"].get("rows"), "head": lines[min(1, len(lines) - 1)][:200], "t": "\n".join(lines[-3:])[:420]})
        else:
            item["t"] = c["text"][:320]
        out_chunks.append(item)

    pages = []
    blank = set(report["no_text_pages"])
    for p in range(1, report["pages"] + 1):
        cnt = per_page.get(p, {})
        pages.append({"p": p, "text": cnt.get("text", 0), "table": cnt.get("table", 0), "figure": cnt.get("figure", 0), "blank": p in blank})

    # ---- featured real examples for the three branch steps ----
    by_id = {c["id"]: c for c in chunks}
    text_ex = next(c for c in chunks if c["metadata"]["kind"] == "text" and "from 32.7% in 2000 to 22.3% in 2020" in c["text"])
    left = by_id["who-whs-2023-p100-table-000"]["text"].split("\n")
    right = by_id["who-whs-2023-p101-table-000"]["text"].split("\n")
    fig_ex = fig_by_id["who-whs-2023-p075-fig2.20"]
    examples = {
        "text": {"id": text_ex["id"], "page": text_ex["page"], "text": text_ex["text"][:620]},
        "table": {"leftId": "who-whs-2023-p100-table-000", "rightId": "who-whs-2023-p101-table-000",
                  "leftHead": left[3], "leftRows": left[4:9], "rightHead": right[1][:330], "rightYears": right[3], "rightRows": right[4:9]},
        "figure": {"id": fig_ex["id"], "page": fig_ex["page"], "caption": fig_ex["caption"], "crop": fig_ex["crop"],
                   "layer": fig_ex["text_in_figure"][len(fig_ex["caption"]):].strip()[:300],
                   "desc": desc.get(fig_ex["id"], "")[:900]},
    }

    # ---- benchmark: dev questions only ----
    dev = [{"id": q["id"], "group": q["group"], "q": q["question"], "a": q.get("expected_answer"),
            "answerable": q["answerable"], "mode": q.get("gold_mode"),
            "gold": [{"p": g["page"], "chunk": g["chunk_id"], "loc": g["locator"]} for g in q.get("gold", [])],
            "why": q.get("absence_reason")} for q in questions if q["split"] == "dev"]
    benchmark = {"counts": bench["counts"], "total": bench["total"], "testHash": bench["test_sha256"][:16], "dev": dev,
                 "testCount": sum(1 for q in questions if q["split"] == "test")}

    # ---- retrieval: whatever has been measured on dev ----
    retrieval = {"configs": []}
    for label, folder, note in (("final", "bonus/results", "index có mô tả thị giác cho hình"),
                                ("novision", "bonus/results/novision", "index chưa có mô tả thị giác (chỉ text layer của hình)")):
        sp = ROOT / folder / "dev-summary.json"
        if not sp.exists():
            continue
        summary = json.loads(sp.read_text(encoding="utf-8"))
        methods = []
        for m, s in summary.items():
            tp = ROOT / folder / f"dev-{m}-traces.json"
            if not tp.exists() or s.get("errors"):
                continue  # incomplete runs are not shown
            traces = json.loads(tp.read_text(encoding="utf-8"))
            methods.append({"method": m, "n": s["n"], "hit1": s["hit1"], "hit3": s["hit3"], "hit5": s["hit5"], "mrr": s["mrr"],
                            "byGroup": s["hit3_by_group"], "ms": s["ms_per_query"], "apiCalls": s["api_calls"],
                            "tokens": s["llm_prompt_tokens"] + s["llm_output_tokens"],
                            "q": {t["query_id"]: {"hit3": t["hit3"], "rank": t["first_gold_rank"],
                                                  "extra": (t["trace"].get("rewritten_queries") or
                                                            [q for st in t["trace"].get("steps", []) for q in st.get("followup_queries", [])]),
                                                  "top": [{"id": r["id"], "p": r["page"], "k": r["kind"], "hit": r["hit"]} for r in t["results"][:5]]}
                                  for t in traces}})
        if methods:
            retrieval["configs"].append({"label": label, "note": note, "methods": methods})

    agent = agent_data(by_id)
    tests = test_data()

    data = {
        "agent": agent, "tests": tests,
        "source": {"title": "World health statistics 2023: Monitoring health for the SDGs", "publisher": "World Health Organization",
                   "isbn": "978-92-4-007432-3", "license": "CC BY-NC-SA 3.0 IGO", "pages": report["pages"],
                   "url": "https://www.who.int/publications/i/item/9789240074323"},
        "stats": {"chunks": len(chunks), "byKind": dict(Counter(c["metadata"]["kind"] for c in chunks)), "figures": len(figures),
                  "described": len(desc), "tablePages": len(report["table_pages"]), "figurePages": len(report["figure_pages"]),
                  "blankPages": report["no_text_pages"], "embedModel": index_stats.get("embedding_model"), "dims": index_stats.get("dimensions"),
                  "indexSeconds": index_stats.get("seconds"), "indexApiCalls": index_stats.get("api_calls"), "dbRows": index_stats.get("db_rows"),
                  "charsEmbedded": index_stats.get("chars_embedded")},
        "pages": pages, "chunks": out_chunks, "examples": examples, "benchmark": benchmark, "retrieval": retrieval, "cropsRendered": crops_ok,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"data.json {OUT.stat().st_size // 1024} KB; chunks {len(out_chunks)}; dev questions {len(dev)}; "
          f"retrieval configs {[(c['label'], [m['method'] for m in c['methods']]) for c in retrieval['configs']]}; crops {crops_ok}")


if __name__ == "__main__":
    main()
