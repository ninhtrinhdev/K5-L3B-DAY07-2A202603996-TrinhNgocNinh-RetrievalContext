# Code

Agent thật nối vào khung [starter/agentic.py](../starter/agentic.py):

| File | Vai trò |
|---|---|
| `agent_real.py` | `GeminiController.decide` (model thật, trả `search` / `answer` / `abstain`), `PgVectorRetriever.search` (pgvector thật, query embedding `gemini-embedding-001` 768 chiều), `self_check` |
| `run_agent_eval.py` | Chạy agent trên một split, lưu trace, tổng hợp số đếm tự động, sinh phiếu chấm thủ công |

Corpus: `day6` (chunk Day 6, chiến lược B, 176 chunk) hoặc `whs` (WHO World Health Statistics 2023, 536 chunk, bonus).
Retrieval: `dense` (mặc định), `rerank` (dense lấy 15 ứng viên, model xếp lại), `hybrid_rerank` (chỉ `whs`; cấu hình đã khóa ở `bonus/config.lock.json`).

```bash
python -X utf8 src/run_agent_eval.py --corpus day6 --split dev --config A-dense --method dense --top-k 5 --budget 6000
python -X utf8 -m unittest discover -s tests -v
```

Cần Docker (Postgres + pgvector, cổng 55433) và `GEMINI_API_KEY` trong `.env`. Biến tùy chọn: `AGENT_MODEL` (mặc định `gemini-3.5-flash-lite`),
`GEMINI_MIN_INTERVAL` (giây giữa các lượt gọi, tránh giới hạn theo phút của gói miễn phí).

Kết quả ở `results/agent/<corpus>-<split>-<config>/`: `traces.json` (từng tool call, tham số, kết quả, context cuối, câu trả lời, citation, lỗi),
`summary.json`, `review_sheet.md` và `reviews.template.json` để chấm thủ công rồi đưa vào `starter/agent_metrics.py`.

Quy ước: chỉ câu hỏi đi vào agent; gold chỉ được đọc sau khi chạy xong để đánh dấu `gold_in_final_context`. Lỗi model hoặc cơ sở dữ liệu được ghi `status: "error"`, không thay bằng kết quả giả.
Test chỉ chạy một lần sau khi chốt cấu hình.
