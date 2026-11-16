"""Run the real agent (Gemini controller + pgvector retriever) over one split and save traces.

  python -X utf8 src/run_agent_eval.py --corpus day6 --split dev --config A-dense --method dense --top-k 5 --budget 6000

Only the question text is passed to the agent. Gold/expected answers are read AFTER the run, to mark whether the gold
evidence reached the final context and to prepare a review sheet for manual grading; they never enter the loop.
Provider/database errors are recorded as status "error" (never replaced by a mock) and listed in the summary.
"""
import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path

import psycopg

import agent_real
from agent_real import GeminiController, PgVectorRetriever, self_check
import common
from agentic import run_agent

ROOT = Path(__file__).resolve().parents[1]
CASES = {"day6": ROOT / "data" / "agent_cases.json", "whs": ROOT / "bonus" / "data" / "questions.json"}


def gold_in_context(events, gold):
    """True when a gold evidence string sits inside a chunk that was in the final packed context (post-hoc, for analysis)."""
    searches = [e for e in events if e["event"] == "search"]
    if not searches:
        return False
    in_ctx = {c["id"]: c for e in searches for c in e["results"] if c["id"] in searches[-1]["context_ids"]}
    return any(g["page"] == c["page"] and g["evidence"] in c["text"] for g in gold for c in in_ctx.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, choices=sorted(CASES))
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--config", required=True, help="name of this configuration, used for the output folder")
    ap.add_argument("--method", default="dense", choices=("dense", "rerank", "hybrid_rerank"))
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--budget", type=int, default=6000, help="context budget in characters")
    ap.add_argument("--max-searches", type=int, default=4)
    ap.add_argument("--ids", nargs="*", help="only these question ids (debugging on dev)")
    ap.add_argument("--out", default="results/agent")
    args = ap.parse_args()
    common.load_env()
    cases = [c for c in json.loads(CASES[args.corpus].read_text(encoding="utf-8")) if c["split"] == args.split]
    if args.ids:
        cases = [c for c in cases if c["id"] in args.ids]
    out_dir = ROOT / args.out / f"{args.corpus}-{args.split}-{args.config}"
    out_dir.mkdir(parents=True, exist_ok=True)
    traces, run_started = [], time.perf_counter()
    stats0 = dict(common.STATS)
    with common.connect() as conn:
        retriever = PgVectorRetriever(conn, args.corpus, args.method)
        for case in cases:
            controller = GeminiController(max_searches=args.max_searches)
            retriever.log = []
            t0 = time.perf_counter()
            tok0 = common.STATS["prompt_tokens"], common.STATS["output_tokens"]
            rec = {"query_id": case["id"], "split": case["split"], "group": case.get("group"), "question": case["question"]}
            try:
                result = run_agent(case["question"], controller, retriever, max_searches=args.max_searches,
                                   top_k=args.top_k, budget=args.budget)  # no filters: none given by the user
                rec.update(status=result["status"], answer=result["answer"], citations=result["citations"], events=result["events"],
                           self_check=self_check(result))
            except (common.ApiError, psycopg.Error, OSError, ValueError) as e:
                rec.update(status="error", answer=None, citations=[], events=[], error=f"{type(e).__name__}: {str(e)[:400]}")
                try:
                    conn.rollback()
                except psycopg.Error:
                    pass
            conn.commit()
            searches = [e for e in rec["events"] if e["event"] == "search"]
            rec.update(search_calls=len(searches), tool_calls=retriever.log, model_calls=controller.calls,
                       final_context=searches[-1]["context"] if searches else "", final_context_ids=searches[-1]["context_ids"] if searches else [],
                       elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
                       prompt_tokens=common.STATS["prompt_tokens"] - tok0[0], output_tokens=common.STATS["output_tokens"] - tok0[1],
                       config={"corpus": args.corpus, "method": args.method, "top_k": args.top_k, "budget_chars": args.budget,
                               "max_searches": args.max_searches, "controller_model": controller.model,
                               "embedding": f"{common.EMBED_MODEL}/{common.EMBED_DIM}", "llm_provider": common.provider()})
            rec["gold_in_final_context"] = gold_in_context(rec["events"], case["gold"]) if case["answerable"] else None
            traces.append(rec)
            print(f"{case['id']:8} {rec['status']:8} searches={rec['search_calls']} gold_in_ctx={rec['gold_in_final_context']} "
                  f"{rec.get('error', '')[:80]}", flush=True)

    answerable = {c["id"]: c["answerable"] for c in cases}
    ok = [t for t in traces if t["status"] != "error"]
    summary = {"corpus": args.corpus, "split": args.split, "config": args.config, "n": len(traces),
               "model": traces[0]["config"]["controller_model"] if traces else None,
               "settings": traces[0]["config"] if traces else None,
               "status": dict(Counter(t["status"] for t in traces)),
               "tool_use": f"{sum(t['search_calls'] > 0 for t in ok)}/{len(ok)}",
               "search_calls_distribution": dict(sorted(Counter(t["search_calls"] for t in ok).items())),
               "answerable_gold_in_final_context": f"{sum(bool(t['gold_in_final_context']) for t in ok if answerable[t['query_id']])}/{sum(answerable[t['query_id']] for t in ok)}",
               "answered_unanswerable_auto": [t["query_id"] for t in ok if not answerable[t["query_id"]] and t["status"] == "answered"],
               "abstained_answerable_auto": [t["query_id"] for t in ok if answerable[t["query_id"]] and t["status"] == "abstain"],
               "numbers_not_in_cited_text": {t["query_id"]: t["self_check"]["numbers_not_in_cited_text"] for t in ok
                                             if t["self_check"].get("applicable") and t["self_check"]["numbers_not_in_cited_text"]},
               "errors": [{"id": t["query_id"], "error": t["error"]} for t in traces if t["status"] == "error"],
               "seconds_total": round(time.perf_counter() - run_started, 1),
               "median_ms_per_question": round(statistics.median(t["elapsed_ms"] for t in traces), 1) if traces else None,
               "prompt_tokens": common.STATS["prompt_tokens"] - stats0["prompt_tokens"],
               "output_tokens": common.STATS["output_tokens"] - stats0["output_tokens"],
               "api_calls": common.STATS["api_calls"] - stats0["api_calls"], "api_retries": common.STATS["retries"] - stats0["retries"],
               "note": "automatic counts only; answer grade, citation support and abstention correctness need a human review (reviews.json)"}
    (out_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_review_files(out_dir, cases, traces)
    print(json.dumps({k: v for k, v in summary.items() if k != "settings"}, ensure_ascii=False, indent=1))


def write_review_files(out_dir, cases, traces):
    """review_sheet.md: what a human needs to grade (answer, cited text). reviews.template.json: empty labels to fill in."""
    by_case = {c["id"]: c for c in cases}
    lines, template = ["# Phiếu chấm thủ công\n", "Chấm answer_grade 0/1/2 (có đáp án), citation_support (từng citation: nguồn có hỗ trợ câu trả lời không), "
                       "abstention_correct (câu thiếu evidence). Đáp án chuẩn chỉ để đối chiếu khi chấm.\n"], []
    for t in traces:
        case = by_case[t["query_id"]]
        lines += [f"## {t['query_id']} · {t['status']} · {'có đáp án' if case['answerable'] else 'thiếu evidence'}",
                  f"**Câu hỏi:** {t['question']}", f"**Đáp án chuẩn:** {case.get('expected_answer') or case.get('expected_behavior') or case.get('absence_reason')}", f"**Agent:** {t['answer']}",
                  f"**Số lượt search:** {t['search_calls']} · gold trong context cuối: {t['gold_in_final_context']}"]
        if t.get("error"):
            lines.append(f"**Lỗi:** {t['error']}")
        texts = {c["id"]: c for e in t["events"] if e["event"] == "search" for c in e["results"]}
        for cid in t["citations"]:
            c = texts.get(cid)
            lines.append(f"- citation `{cid}` (tr. {c['page']}): {c['text'][:700]!r}" if c else f"- citation `{cid}`: KHÔNG có trong kết quả")
        lines.append("")
        if t["status"] != "error":
            label = {"answer_grade": None} if case["answerable"] else {"abstention_correct": None}
            template.append({"query_id": t["query_id"], **label, "citation_support": [None] * len(t["citations"]), "reason": ""})
    (out_dir / "review_sheet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "reviews.template.json").write_text(json.dumps(template, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
