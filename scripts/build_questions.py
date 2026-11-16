"""Build Day 7 benchmark files from the Day 6 dev questions + newly written test questions.

Outputs (JSON arrays, UTF-8):
  data/questions.json    answerable questions only (baseline-compatible: gold = exact substring of one chunk)
  data/agent_cases.json  every question incl. the 'search_and_abstain' ones (see data/README.md)
Nothing here runs retrieval; evidence is checked only for exact presence in the stated chunk/page.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY6_Q = Path("E:/VinUni/K5-L3B-DAY06-TrinhNgocNinh-2A202603996-DataIngestion/starter/benchmark/questions.json")
SRC = "who-preeclampsia-2011"
chunks = json.loads((ROOT / "data/chunks.json").read_text(encoding="utf-8"))
by_id = {c["id"]: c for c in chunks}


def slice_between(chunk_id, start, end):
    """Exact substring of chunk text from `start` through `end` (inclusive)."""
    t = by_id[chunk_id]["text"]
    i = t.index(start)
    j = t.index(end, i) + len(end)
    return chunk_id, t[i:j]


def gold_item(chunk_id, evidence):
    c = by_id[chunk_id]
    assert evidence in c["text"], (chunk_id, evidence)
    return {"source_id": c["source_id"], "page": c["page"], "evidence": evidence, "chunk_id": chunk_id}


# ---------- dev: Day 6 dev questions d01-d15 (quotes re-validated against exported chunks) ----------
day6 = json.loads(DAY6_Q.read_text(encoding="utf-8"))["questions"]
answerable = []
dropped = []
for q in day6:
    if q["split"] != "dev":
        continue  # Day 6 test was viewed together with dev results -> NOT reused as independent test
    gold = []
    for e in q["evidence"]:
        hits = [c for c in chunks if c["page"] == e["page"] and e["quote"] in c["text"]]
        if hits:
            gold.append({"source_id": SRC, "page": e["page"], "evidence": e["quote"], "chunk_id": hits[0]["id"]})
        else:
            dropped.append((q["id"], e["page"]))  # quote spans table markup/<br>; alternative gold kept
    assert gold, q["id"]
    item = {"id": q["id"], "split": "dev", "question": q["question"], "expected_answer": q["expected_answer"],
            "gold": gold, "day6_type": q["type"], "answerable": True, "expected_behavior": "search_and_answer"}
    if q.get("filter"):
        item["filter"] = q["filter"]
    answerable.append(item)

# ---------- test: 5 NEW answerable questions (topics not used in dev), written before any retrieval ----------
T = []
cid, ev = slice_between("who-preeclampsia-2011-p018-002", "3. Restriction in dietary salt intake", "Weak recommendation.)")
T.append(("t01", "Does WHO recommend restricting dietary salt intake during pregnancy to prevent pre-eclampsia, and how strong is the recommendation?",
          "No: restriction of dietary salt intake is not recommended (moderate-quality evidence, weak recommendation).", [(cid, ev)]))
cid, ev = slice_between("who-preeclampsia-2011-p023-002", "A Cochrane systematic review of 46 RCTs", "4282 women")
T.append(("t02", "How many randomized trials and how many women were in the Cochrane review of antihypertensive drug treatment for mild to moderate hypertension in pregnancy?",
          "46 RCTs involving a total of 4282 women.", [(cid, ev)]))
cid, ev = slice_between("who-preeclampsia-2011-p024-005", "calcium channel blockers (nifedipine and isradipine) showed", "RR 0.33, 95% CI 0.15–0.70)")
T.append(("t03", "In the review on severe hypertension, which drug class outperformed hydralazine for persistent high blood pressure, and what were the number of trials, women and the risk ratio?",
          "Calcium channel blockers (nifedipine and isradipine): five trials, 263 women, RR 0.33 (95% CI 0.15–0.70).", [(cid, ev)]))
cid, ev = slice_between("who-preeclampsia-2011-p039-001", "This guideline will be updated after five years", "new evidence showing a need to change the recommendations.")
T.append(("t04", "When will this guideline be updated?",
          "After five years, or earlier following identification of new evidence showing a need to change the recommendations.", [(cid, ev)]))
cid, ev = slice_between("who-preeclampsia-2011-p038-004", "3. Health-care facilities using magnesium sulfate", "magnesium sulfate toxicity.")
T.append(("t05", "What must facilities using magnesium sulfate have available in case of toxicity?",
          "Calcium gluconate.", [(cid, ev)]))
for qid, question, ans, golds in T:
    answerable.append({"id": qid, "split": "test", "question": question, "expected_answer": ans,
                       "gold": [gold_item(c, e) for c, e in golds], "answerable": True,
                       "expected_behavior": "search_and_answer"})

# ---------- unanswerable (near-topic, absence verified by keyword search of all 48 PDF pages) ----------
absent = [
    {"id": "d16", "split": "dev", "question": "Does the guideline recommend low-molecular-weight heparin to prevent pre-eclampsia?",
     "absence_reason": "Heparin không xuất hiện ở bất kỳ trang nào của PDF (48 trang, kiểm bằng tìm từ khóa 'heparin'); tài liệu chỉ bàn aspirin/antiplatelets (tr. 21-23)."},
    {"id": "d17", "split": "dev", "question": "What starting dose of labetalol does the guideline give for severe hypertension in pregnancy?",
     "absence_reason": "Labetalol chỉ xuất hiện trong so sánh hiệu quả với hydralazine (tr. 24-25, 28, 35); không có liều mg nào cho labetalol/nifedipine/hydralazine (không khớp 'N mg' cùng chunk với tên thuốc)."},
    {"id": "t06", "split": "test", "question": "Does the guideline recommend uterine artery Doppler screening to predict pre-eclampsia?",
     "absence_reason": "'Doppler' không xuất hiện trong PDF (48 trang); 'screening' chỉ ở tr. 12 và 37 (nói về công cụ sàng lọc cho nhân viên y tế cộng đồng), không đề cập Doppler."},
    {"id": "t07", "split": "test", "question": "Does the guideline recommend fish oil (omega-3) supplementation to prevent pre-eclampsia?",
     "absence_reason": "'fish oil' và 'omega' không xuất hiện trong PDF (48 trang); phần phòng ngừa chỉ gồm nghỉ ngơi, muối, canxi, vitamin D, chống oxy hóa, antiplatelets."},
]
for a in absent:
    a.update({"answerable": False, "expected_behavior": "search_and_abstain"})

# ---------- write ----------
def strip_internal(q):
    q = dict(q)
    q["gold"] = [{k: g[k] for k in ("source_id", "page", "evidence")} for g in q["gold"]]
    return q

full = answerable + absent
for name, data in (("questions.json", [strip_internal(q) for q in answerable]), ("agent_cases.json", [strip_internal(q) if q["answerable"] else q for q in full]),
                   ("questions_with_chunk_ids.json", full)):
    (ROOT / "data" / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
from collections import Counter
print(Counter((q["split"], q["answerable"]) for q in full))
print("Day6 gold alternatives dropped (not an exact chunk substring):", dropped)
