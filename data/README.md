# Định dạng dữ liệu

Các file `example_*.json` chỉ minh họa định dạng, không đủ để nộp bài. Dữ liệu thật là JSON array UTF-8; nếu dùng định dạng khác, ghi cách chuyển trong README.

- **Chunk:** `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID phải duy nhất; giữ phiên bản hoặc ngày nếu có.
- **Câu có đáp án:** `id`, `split` (`dev` hoặc `test`), `question`, `expected_answer`, `gold`: danh sách `{source_id, page, evidence}`. Với schema mẫu, mỗi evidence phải nằm trọn trong một chunk đúng nguồn và trang; các phần tử `gold` là evidence thay thế. Với câu multi-hop cần nhiều đoạn, bạn có thể mở rộng schema, ghi rõ nhóm evidence bắt buộc và cách chấm. Có thể thêm `filter` do người dùng cung cấp trước.
- **Câu thiếu evidence:** `id`, `split`, `question`, `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`. Xem `agent_cases_example.json`.

Không đưa `gold` hoặc nhãn đáp án vào model và retrieval tool. Ghi nguồn dữ liệu và quyền sử dụng. Cách chuyển một số định dạng Day 6: [starter/README.md](../starter/README.md).

---

# Dữ liệu của bài này (Day 6 → Day 7)

## Nguồn và quyền dùng
- Tài liệu: WHO, *Recommendations for Prevention and treatment of pre-eclampsia and eclampsia* (2011, ISBN 978 92 4 154833 5), `source_id = who-preeclampsia-2011`, `source = content.pdf`. Tải từ https://www.who.int/publications/i/item/9789241548335.
- Quyền: © WHO 2011, **không phải giấy phép mở** (trang 4 của PDF); chỉ dùng cho bài lab. **Không commit file PDF.** `chunks.json` chứa trích đoạn văn bản của tài liệu — cân nhắc trước khi đẩy lên repo công khai (xem Day 6 `starter/data/manifest.json`).
- Trang = số trang **vật lý** trong PDF; 31 trang nội dung (9–39).

## Kết nối Day 6
| Mục | Giá trị |
|---|---|
| Chunk | Day 6 chiến lược **B** (`by_paragraph`, tối đa 1000 ký tự, 176 chunk); ID giữ nguyên `who-preeclampsia-2011-pNNN-NNN` |
| Embedding | Google Gemini API `gemini-embedding-001`, **768 chiều** (Matryoshka cắt rồi chuẩn hóa L2); tài liệu `RETRIEVAL_DOCUMENT`, câu hỏi `RETRIEVAL_QUERY` |
| Vector store | PostgreSQL 16.16 + pgvector 0.8.7 (`pgvector/pgvector:0.8.7-pg16`, cổng 55433, DB `day6_lab`, bảng `day6_chunks`, khóa `(strategy, chunk_id)`), cosine `<=>`, tìm chính xác |
| Cách kết nối | Khởi động container Day 6 (`docker start day6_student_starter-postgres-1` hoặc `docker compose up -d` trong `starter/` của Day 6); `DATABASE_URL` mặc định trong `scripts/export_day6.py`. Query embedding **phải** dùng cùng model/số chiều/task như trên. |
| Xuất chunk | `python -X utf8 scripts/export_day6.py` → `data/chunks.json` (chỉ text + metadata, không có vector, không có khóa) |

## Bộ câu hỏi (sinh bằng `python -X utf8 scripts/build_questions.py`)
| Split | Có đáp án | Thiếu bằng chứng | File |
|---|---:|---:|---|
| dev | 15 (d01–d15, từ Day 6) | 2 (d16, d17) | |
| test | 5 (t01–t05, **mới**) | 2 (t06, t07) | |
| **Tổng** | 20 | 4 | 24 |

- `questions.json`: chỉ câu có đáp án, tương thích `starter/baseline.py` (gold = chuỗi **nguyên văn** nằm trong một chunk đúng nguồn và trang).
- `agent_cases.json`: tất cả 24 câu; câu thiếu bằng chứng có `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`.
- `questions_with_chunk_ids.json`: bản có `chunk_id` trong gold, để truy ngược evidence → chunk → trang. **Không đưa cho agent/retrieval.**
- **Test Day 6 (t01–t05 cũ) không dùng làm test:** chúng được xem cùng kết quả dev ở Day 6, nên 5 câu test mới được viết lại ở đây từ các chủ đề dev không dùng (muối, thuốc hạ huyết áp, canxi gluconate, cập nhật guideline). Các câu test viết **trước khi chạy bất kỳ truy xuất nào** trên Day 7.
- 6 alternative gold của Day 6 nằm ở bảng Box 1 (tr. 10–11) bị loại vì trích dẫn không phải chuỗi con nguyên văn của chunk (do markup bảng); mỗi câu vẫn còn ≥1 gold ở trang chi tiết.
- Câu thiếu bằng chứng: từ khóa tìm không thấy trong cả 48 trang PDF (heparin, Doppler, fish oil/omega, liều labetalol); lý do ghi ở `absence_reason`. Chưa chứng minh "toàn tài liệu thiếu" ngoài việc tìm từ khóa — kiểm tay thêm nếu cần.
- **Đóng băng test:** SHA-256 (JSON chuẩn hóa, `sort_keys`) của mảng test, 16 ký tự đầu: `questions.json` = `cb9572afa57289b3` (5 câu), `agent_cases.json` = `ecdfe19e1c7be8cf` (7 câu). Không sửa test sau khi xem kết quả; nếu sửa, tạo test mới và ghi lại.

## Kiểm tra
`python -m unittest discover -s tests -v` (20 test, gồm `tests/test_data.py`: ID duy nhất, đủ số câu, gold là chuỗi con nguyên văn của chunk đúng trang, câu thiếu có `absence_reason`, dev/test không trùng).
