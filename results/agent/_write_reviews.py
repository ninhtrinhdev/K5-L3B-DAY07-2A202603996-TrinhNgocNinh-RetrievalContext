"""Manual labels: each answer was read against the text of every chunk it cites (see `reason`). Edit reviews.json by hand if you disagree, then re-run starter/agent_metrics.py."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# (grade, reason) for answerable cases, keyed by query id; every cited chunk was read and supports its claim unless listed in BAD_CITE
OK = "Khớp đáp án chuẩn; đoạn nguồn trích nêu đúng ý đó."
GRADE = {}
for i in ["d01", "d02", "d03", "d04", "d05", "d06", "d07", "d10", "d11", "d12", "d13", "d14", "d15", "t01", "t02", "t03", "t04", "t05",
          "d-tb1", "d-tb2", "d-tb3", "d-im1", "d-im2", "d-ch1", "d-ch2", "d-ch3", "d-mh1", "d-mh2", "d-mh3", "d-tx1", "d-tx2", "d-tx3"]:
    GRADE[i] = (2, OK)
GRADE["d08"] = (0, "Từ chối. Câu hỏi mơ hồ: cùng chữ với d09 nhưng đáp án chuẩn khác (13 RCT/15 730 vs 60 RCT/37 720), tài liệu có nhiều Cochrane review. Theo luật script, từ chối câu có đáp án chấm 0.")
GRADE["d09"] = (0, "Từ chối vì cùng lý do với d08 (câu hỏi không chỉ rõ review nào). Chấm 0 theo luật script.")
GRADE["d-im3"] = (0, "Sai: agent trả lời Canada là 'Yes' theo mô tả hình do model vision viết, trong khi hình thật tô Canada là 'No' (đáp án chuẩn). Lỗi nằm ở mô tả hình, không ở agent.")
GRADE["d-mh2"] = (2, "620 (tr. 97) và 223 (tr. 15) đúng; hiệu 397 tính đúng; đáp án chuẩn cũng nêu 397.")
GRADE["d-ch2"] = (2, "4,0% và 2,7% đúng; nguồn ghi giai đoạn đầu là 2000-2009 (đáp án chuẩn viết 2000-2010), không đổi ý nghĩa.")
# run-specific labels (override GRADE) and citation labels; "d-im3": the cited chunk's vision description contradicts the real figure
RUN_GRADE = {
    ("whs-dev-D-hybrid-rerank", "d-ch3"): (2, "Đúng 92% và 70%; nhưng citation thứ hai (bảng tr. 126 về tỷ lệ còi cọc) không liên quan tới câu hỏi."),
    ("whs-dev-C-dense", "d-mh1"): (0, "Từ chối câu có đáp án: agent tìm 4 lượt nhưng không lấy được hàng Mali ở bảng tr. 101 vào context. Chấm 0 theo luật script."),
    ("whs-dev-C-dense", "d-ch2"): (1, "Số đúng (4,0% và 2,7%) nhưng câu trả lời có thêm marker trích dẫn sai ID [who-whs-2013-p018-text-002] (không tồn tại)."),
}
BAD_CITE = {("whs-dev-C-dense", "d-im3"): [False], ("whs-dev-D-hybrid-rerank", "d-im3"): [False],
            ("whs-dev-D-hybrid-rerank", "d-ch3"): [True, False]}
WRONG_IM5 = "Chưa đúng/đủ: đáp án là 'Yes' nhưng agent liệt kê Trung Quốc vào cả 'Yes', 'No', 'Not a participant' và 'Not applicable' (tự mâu thuẫn, dựa trên mô tả hình liệt kê sai); citation không xác định được trạng thái."
RUN_GRADE.update({
    ("whs-test-D-hybrid-rerank", "t-im5"): (1, WRONG_IM5),
    ("whs-test-C-dense", "t-im5"): (1, WRONG_IM5),
    ("whs-test-D-hybrid-rerank", "t-ch5"): (2, "Đúng 32%, 23%, 28%; nhưng hai citation thêm (bảng tr. 126 và 127 về chỉ số khác) không chứa số liệu WASH của Châu Phi: citation thừa, sai nguồn."),
    ("whs-test-C-dense", "t-tb6"): (0, "Từ chối câu có đáp án: không đưa được bảng tr. 102 (hàng Viet Nam) vào context. Chấm 0 theo luật script."),
    ("whs-test-C-dense", "t-mh1"): (0, "Từ chối câu có đáp án: không lấy được bảng tr. 100-101 (hàng Mexico) vào context. Chấm 0 theo luật script."),
})
BAD_CITE.update({("whs-test-D-hybrid-rerank", "t-im5"): [False], ("whs-test-C-dense", "t-im5"): [False],
                 ("whs-test-D-hybrid-rerank", "t-ch5"): [True, False, False]})
RUNS = {"day6-dev-A-dense": "day6", "day6-dev-B-rerank": "day6", "whs-dev-C-dense": "whs", "whs-dev-D-hybrid-rerank": "whs",
        "day6-test-A-dense": "day6", "day6-test-B-rerank": "day6", "whs-test-C-dense": "whs", "whs-test-D-hybrid-rerank": "whs"}
CASES = {"day6": ROOT / "data" / "agent_cases.json", "whs": ROOT / "bonus" / "data" / "questions.json"}

for run, corpus in RUNS.items():
    cases = {c["id"]: c for c in json.loads(CASES[corpus].read_text(encoding="utf-8"))}
    out = []
    for t in json.loads((ROOT / "results/agent" / run / "traces.json").read_text(encoding="utf-8")):
        if t["status"] == "error":
            continue  # provider errors are excluded by the course script and reported separately
        n = len(t["citations"])
        support = BAD_CITE.get((run, t["query_id"]), [True] * n)
        if cases[t["query_id"]]["answerable"]:
            grade, reason = RUN_GRADE.get((run, t["query_id"])) or GRADE.get(t["query_id"], (2, OK))
            out.append({"query_id": t["query_id"], "answer_grade": grade, "citation_support": support, "reason": reason})
        else:
            assert t["status"] == "abstain" and n == 0
            out.append({"query_id": t["query_id"], "abstention_correct": True, "citation_support": [],
                        "reason": "Từ chối đúng, không thêm khẳng định nào; đã tìm bằng nhiều câu tìm trước khi từ chối."})
    (ROOT / "results/agent" / run / "reviews.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(run, len(out))
