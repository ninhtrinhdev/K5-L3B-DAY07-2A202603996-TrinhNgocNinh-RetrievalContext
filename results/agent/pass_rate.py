"""Pass/fail per test question (ADVANCED.md section 3) from traces.json + reviews.json, and course metrics via starter/agent_metrics.py.

Answerable: pass only when status is answered, answer_grade == 2 and EVERY citation is labelled as supporting the answer.
Unanswerable: pass when the agent refused (abstention_correct). Error / timeout / no result: fail, kept in the denominator.
Writes pass_rate.json and metrics.json next to each run. Usage: python -X utf8 results/agent/pass_rate.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "starter"))
from agent_metrics import aggregate  # noqa: E402

CASES = {"day6": ROOT / "data" / "agent_cases.json", "whs": ROOT / "bonus" / "data" / "questions.json"}
RUNS = [("day6-dev-A-dense", "day6"), ("day6-dev-B-rerank", "day6"), ("whs-dev-C-dense", "whs"), ("whs-dev-D-hybrid-rerank", "whs"),
        ("day6-test-A-dense", "day6"), ("day6-test-B-rerank", "day6"), ("whs-test-C-dense", "whs"), ("whs-test-D-hybrid-rerank", "whs")]

for run, corpus in RUNS:
    d = ROOT / "results" / "agent" / run
    split = "test" if "-test-" in run else "dev"
    cases = [c for c in json.loads(CASES[corpus].read_text(encoding="utf-8")) if c["split"] == split]
    traces = json.loads((d / "traces.json").read_text(encoding="utf-8"))
    reviews = {r["query_id"]: r for r in json.loads((d / "reviews.json").read_text(encoding="utf-8"))}
    tr = {t["query_id"]: t for t in traces}
    rows, groups = [], defaultdict(lambda: [0, 0])
    for c in cases:
        t, r = tr[c["id"]], reviews.get(c["id"])
        if t["status"] == "error":
            ok, why = False, "lỗi hệ thống: " + t["error"][:90]
        elif c["answerable"]:
            ok = t["status"] == "answered" and r["answer_grade"] == 2 and all(r["citation_support"])
            why = r["reason"]
        else:
            ok, why = bool(r["abstention_correct"]), r["reason"]
        g = c.get("group") or c.get("day6_type") or "all"
        groups["unanswerable" if not c["answerable"] else g][1] += 1
        groups["unanswerable" if not c["answerable"] else g][0] += ok
        rows.append({"query_id": c["id"], "group": g, "answerable": c["answerable"], "status": t["status"], "pass": ok, "reason": why})
    n, N = sum(r["pass"] for r in rows), len(rows)
    report = {"run": run, "pass": f"{n}/{N}", "rate_percent": round(100 * n / N, 1), "needs_27_of_30": N == 30 and n >= 27,
              "by_group": {g: f"{a}/{b}" for g, (a, b) in sorted(groups.items())}, "per_question": rows}
    (d / "pass_rate.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    metrics = {"split": split, **aggregate(cases, traces, list(reviews.values()))}
    (d / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    g = metrics["grounded_answer"]
    print(f"{run:28} pass {n}/{N} ({report['rate_percent']}%) | answer 0/1/2 = {g['0']}/{g['1']}/{g['2']} mean {None if g['mean'] is None else round(g['mean'], 2)} "
          f"| cite {metrics['citation_validity']['n']}/{metrics['citation_validity']['N']} | abstain ok {metrics['abstention']['n']}/{metrics['abstention']['N']} "
          f"| false abstain {metrics['false_abstention']['n']}/{metrics['false_abstention']['N']} | errors {metrics['provider_errors']}")
    if "whs-test" in run:
        print("   by group:", report["by_group"])
