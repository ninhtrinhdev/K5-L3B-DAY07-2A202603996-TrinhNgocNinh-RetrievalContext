# Báo cáo Day 7 — Agentic RAG

Trịnh Ngọc Ninh · MSSV 2A202603996 · K5-L3B. Mọi con số dưới đây lấy từ file trong repo (đường dẫn ghi ở từng mục); không có số nào là mock.

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk.**
  - *Phần cơ bản (Day 6):* WHO, *Recommendations for prevention and treatment of pre-eclampsia and eclampsia* (2011, ISBN 978 92 4 154833 5), 31 trang nội dung (tr. 9–39), 176 chunk chiến lược B (≤1000 ký tự). © WHO 2011, **không phải giấy phép mở**, chỉ dùng cho bài lab; không commit PDF. `data/chunks.json` chứa trích đoạn văn bản, **cần để repo ở chế độ riêng tư** (xem [data/README.md](../../data/README.md)).
  - *Thử thách nâng cao:* WHO, *World health statistics 2023* (ISBN 978-92-4-007432-3), **136 trang**, giấy phép CC BY-NC-SA 3.0 IGO, 536 chunk = 336 text + 156 bảng + 44 hình, gộp trong **một** index. Trang trống không có nội dung (2, 6, 12, 44, 94, 132–135) được ghi trong `bonus/data/extract_report.json`. Quyết định tài liệu và pipeline: [docs/ADR-001](../../docs/ADR-001-bonus-document-and-pipeline.md).
- **Vector store, embedding, phiên bản, số chiều.** PostgreSQL 16.16 + pgvector 0.8.7 (Docker, cổng 55433), cosine, tìm chính xác. Embedding `gemini-embedding-001`, **768 chiều** (cắt Matryoshka rồi chuẩn hóa L2); tài liệu `RETRIEVAL_DOCUMENT`, câu hỏi `RETRIEVAL_QUERY`. Day 6: bảng `day6_chunks`; WHO: bảng `day7_chunks` (`corpus = who-whs-2023`).
- **Agent model, cách chạy, phân chia dev/test.** Controller và rerank dùng `gemini-3.5-flash-lite`, nhiệt độ 0. Dev/test chia **trước khi thử nghiệm**:

  | Bộ | Dev | Test |
  |---|---|---|
  | Day 6 (cơ bản) | 15 có đáp án + 2 thiếu evidence | 5 + 2 (viết mới, không dùng lại test Day 6 vì đã bị xem cùng dev) |
  | WHO (nâng cao) | 15 + 3 (mỗi nhóm bảng/ảnh/biểu đồ/multi-hop/text 3 câu) | **24 + 6**: bảng 6, ảnh 5, biểu đồ 5, multi-hop 4, text 4, thiếu evidence 6 |

  Hash test WHO: `75aed127…954984d2`, kiểm lại trước khi chạy (`bonus/config.lock.json`).
- **Câu có/thiếu evidence và tiêu chí chấm.** Câu có đáp án ghi `gold` = trang + chuỗi nguyên văn nằm trong đúng một chunk (kiểm bằng `tests/test_data.py` và `bonus/build_benchmark.py`: 0 lỗi). Câu thiếu evidence ghi `absence_reason` và đã kiểm từ khóa vắng mặt trong toàn tài liệu. Gold chỉ đọc **sau** khi chạy (để đánh dấu "bằng chứng có trong context"), không bao giờ đi vào agent hay retrieval.

## Retrieval và thử nghiệm

Quy tắc chọn (công bố trước khi chạy test, `results/agent/config.lock.json`): Hit@3 cao nhất trên dev; hòa thì xét MRR, rồi số lần từ chối oan; chi phí và thời gian được báo cáo nhưng không dùng để phá hòa. Ba lượt chạy LLM của retrieval trên Day 6 và toàn bộ agent dùng cùng model qua OpenRouter; retrieval WHO dùng Gemini API trực tiếp.

### Corpus Day 6 (15 câu dev, 5 câu test có đáp án)

| Cấu hình | Phương pháp (top-k 10) | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Hit@5 / MRR | Thời gian / lượt gọi |
|---|---|---|---|---|---|---|---|
| Baseline | Dense (pgvector) | — | dev | 12/15 | 12/15 | 13/15 · 0,822 | 638 ms/câu |
| Phương pháp 2 | BM25 | Từ khóa chính xác bù dense | dev | 11/15 | 13/15 | 14/15 · 0,817 | 0,5 ms/câu |
| Phương pháp 3 | Hybrid RRF k=60 | Gộp thứ hạng dense + BM25 | dev | 11/15 | **14/15** | 14/15 · 0,819 | 5 ms/câu |
| Cải thiện 1 | Hybrid → **rerank** 15 ứng viên | Model đưa đoạn đúng lên hạng 1 | dev | **13/15** | **14/15** | 14/15 · **0,910** | 2,2 s/câu, 15 lượt gọi |
| Cải thiện 2 | Viết lại query (2 câu thêm) | Mở rộng cách diễn đạt | dev | 11/15 | 11/15 | 12/15 · 0,776 | 2,6 s/câu |
| Thử thêm | Nhiều chặng | Hỏi tiếp phần còn thiếu | dev | 11/15 | 13/15 | 13/15 · 0,806 | 1,2 s/câu |
| Cấu hình đã chọn (rerank) | | | **test** | **5/5** | **5/5** | 5/5 · 1,000 | 1,2 s/câu |
| Baseline (dense) | | | test | 3/5 | 5/5 | 5/5 · 0,767 | 0,65 s/câu |
| (BM25 · hybrid) | | | test | 4/5 · 4/5 | 5/5 · 5/5 | 5/5 · 0,867 / 0,900 | |

File: `results/retrieval-day6/{dev,test}-summary.json` và `*-traces.json` (mỗi câu có ID, score, rank, nguồn, trang, hit).

### Corpus WHO (15 câu dev, 24 câu test có đáp án)

| Phương pháp | dev Hit@1 | dev Hit@3 | dev MRR | test Hit@1 | test Hit@3 | test Hit@5 | test MRR | Thời gian test / lượt gọi |
|---|---|---|---|---|---|---|---|---|
| Dense (baseline) | 10/15 | 14/15 | 0,844 | 14/24 | 18/24 | 22/24 | 0,806 | 6 ms |
| BM25 | 7/15 | 9/15 | 0,643 | 16/24 | 19/24 | 20/24 | 0,831 | 2 ms |
| Hybrid RRF | 8/15 | 12/15 | 0,755 | 17/24 | 21/24 | 23/24 | 0,920 | 8 ms |
| **Rerank (đã chốt)** | **12/15** | **14/15** | **0,967** | **17/24** | **22/24** | **23/24** | **0,951** | 15,1 s, 55 lượt gọi |
| Viết lại query | 10/15 | 11/15 | 0,821 | 15/24 | 21/24 | 22/24 | 0,854 | 13,9 s |
| Nhiều chặng | 8/15 | 12/15 | 0,727 | 16/24 | 21/24 | 23/24 | 0,866 | 8,4 s |

File: `bonus/results/{dev,test}-summary.json`, `bonus/config.lock.json` (rerank chốt trên dev, test chạy một lần). Hit@3 test theo nhóm của rerank: bảng 5/6, ảnh 5/5, biểu đồ 5/5, multi-hop 3/4, text 4/4. Thêm thử nghiệm index có/không có mô tả thị giác cho hình: `bonus/results/novision/` (dev).

**Hai lỗi dev, nguyên nhân, cách thử, lý do chọn cấu hình.**
1. *Hybrid kém dense trên WHO dev (12/15 so với 14/15)* nhưng hơn dense trên test (21/24 so với 18/24) và trên Day 6 dev (14/15 so với 12/15). Giả thuyết (chưa kiểm riêng): BM25 bắt tốt tên chỉ số trong bảng nhưng kéo các bảng annex trùng tiêu đề lên, làm hybrid trượt các câu multi-hop trên dev (`d-im3`, `d-mh1`, `d-mh2`). Cách thử: so sánh lại trên test sau khi khóa. Kết luận: hybrid không ổn định giữa các tập; rerank sửa được cả hai (dev 14/15 ở cả hai corpus, MRR cao nhất) nên được chọn.
2. *Multi-hop cần hai hàng bảng* (ví dụ Mali: tr. 100 và tr. 101): RRF của rewrite/multi-stage vẫn đẩy hàng bảng thứ hai xuống dưới top 3. Cách thử: rewrite và multi-stage tạo đúng từng nửa câu tìm nhưng **không cải thiện** (rewrite 11/15, multi-stage 12/15). Giới hạn: lỗi nằm ở cách gộp, chưa sửa.

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, context, lỗi.** Một tool `search(query)` (kiến trúc ở [src/agent_real.py](../../src/agent_real.py), vòng lặp ở `starter/agentic.py`). Controller là model thật; lượt đầu bắt buộc tìm; tối đa **4 lượt tìm**; dừng khi trả lời có citation hợp lệ, khi model `abstain`, hoặc hết lượt (→ từ chối). Top-k **5**; context budget **6000 ký tự** (Day 6) / **12 000** (WHO, vì chunk bảng dài); chunk khử trùng lặp theo ID, giữ theo thứ tự tìm. Citation phải là ID có trong context cuối và có marker `[id]` trong câu trả lời. Retriever là pgvector thật (dense) hoặc dense + BM25 + rerank. Lỗi model/CSDL được ghi `status: "error"` kèm thông điệp, **không thay bằng mock**; trong bonus mỗi lỗi tính là không đạt và vẫn nằm trong mẫu số.
- **Đường dẫn trace, nhãn, lệnh, thời gian, chi phí.** `results/agent/<corpus>-<split>-<config>/` gồm `traces.json` (từng tool call, tham số, kết quả, context cuối, câu trả lời, citation, token, thời gian), `reviews.json` (nhãn + lý do), `metrics.json`, `pass_rate.json`, `review_sheet.md`, `summary.json`.

  ```bash
  python -X utf8 src/run_agent_eval.py --corpus whs --split test --config D-hybrid-rerank --method hybrid_rerank --top-k 5 --budget 12000
  python -X utf8 results/agent/pass_rate.py        # tính nhãn -> pass/fail và starter/agent_metrics.py
  ```
  Chi phí: gói miễn phí Gemini (0 USD) cho lần chạy trực tiếp; các lần chạy OpenRouter ước tính theo token × giá niêm yết ($0,30/$2,50 mỗi triệu token vào/ra): WHO test chọn ≈ $0,16 (426 nghìn token vào), baseline ≈ $0,09, Day 6 test ≈ $0,03, dev ≈ $0,14.

| Cấu hình / split | Tool use | Số lượt gọi (phân bố) | Grounded answer 0/1/2 · trung bình | Citation hỗ trợ | Câu có citation | Abstention đúng | Từ chối nhầm | Lỗi |
|---|---|---|---|---|---|---|---|---|
| Day 6 dense · dev | 17/17 | 1: 15 · 3: 2 | 2/0/13 · 1,73 | 20/20 | 13/13 | 2/2 | 2/15 | 0 |
| Day 6 rerank · dev | 17/17 | 1: 15 · 2: 1 · 3: 1 | 2/0/13 · 1,73 | 22/22 | 13/13 | 2/2 | 2/15 | 0 |
| Day 6 dense · **test** | 7/7 | 1: 5 · 3: 2 | 0/0/5 · 2,00 | 6/6 | 5/5 | 2/2 | 0/5 | 0 |
| Day 6 rerank · **test** (chọn) | 7/7 | 1: 5 · 2: 2 | 0/0/5 · 2,00 | 6/6 | 5/5 | 2/2 | 0/5 | 0 |
| WHO dense · dev | 18/18 | 1: 13 · 2: 2 · 3: 2 · 4: 1 | 2/1/12 · 1,67 | 17/18 | 15/15 | 3/3 | 1/15 | 0 |
| WHO hybrid+rerank · dev | 18/18 | 1: 16 · 2: 2 | 1/0/14 · 1,87 | 18/20 | 15/15 | 3/3 | 0/15 | 0 |
| WHO dense · **test** | 29/29 | 1: 20 · 2: 4 · 3: 5 | 2/1/20 · 1,78 | 24/25 | 21/21 | 6/6 | 2/23 | **1** |
| WHO hybrid+rerank · **test** (chọn) | 30/30 | 1: 24 · 2: 4 · 3: 2 | 0/1/23 · 1,96 | 31/34 | 24/24 | 6/6 | 0/24 | 0 |

Bằng chứng chuẩn có trong context cuối (đo sau khi chạy): Day 6 dev 14/15 → 15/15 (dense → rerank), Day 6 test 5/5 cả hai, WHO dev 15/15 cả hai, WHO test 21/23 (dense) → **24/24** (chọn).

### Các câu test đã đọc (Day 6, cấu hình chọn rerank, 5 câu có đáp án + 2 thiếu evidence)

| Query ID | Loại | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| t01 | có đáp án | search "dietary salt intake pregnancy pre-eclampsia WHO recommendation strength" → tr. 18, 11, 18, 18, 10 | Không khuyến cáo hạn chế muối; mức khuyến cáo yếu, bằng chứng trung bình [p018-002] [p011-000] | 2; cả hai citation nêu đúng ý |
| t02 | có đáp án | search "Cochrane review antihypertensive …" → tr. 23 ×4, 24 | 46 RCT, 4282 phụ nữ [p023-002] | 2; số khớp đoạn nguồn |
| t03 | có đáp án | search "severe hypertension hydralazine …" → tr. 25, 24 ×3 | Chẹn kênh canxi; 5 thử nghiệm, 263 phụ nữ, RR 0,33 (0,15–0,70) [p024-005] | 2; |
| t04 | có đáp án | search "guideline update date" → tr. 39 … | Cập nhật sau 5 năm hoặc khi có bằng chứng mới [p039-001]. *Lần chạy đầu của test này bị lỗi rerank (JSON bọc trong mảng); đã sửa trình phân tích, chạy lại cả test, không đổi prompt/câu hỏi/cấu hình.* | 2 |
| t05 | có đáp án | search "magnesium sulfate toxicity facilities available" → tr. 38 … | Canxi gluconat [p038-004] | 2 |
| t06 | thiếu evidence | 2 lượt tìm "uterine artery Doppler …" | Từ chối, lý do: đoạn tìm được không nói về Doppler động mạch tử cung | đạt; không khẳng định thêm |
| t07 | thiếu evidence | 2 lượt tìm "fish oil omega-3 …" | Từ chối | đạt |

### Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn

- **Trước/sau sửa định dạng citation (Day 6 dev).** Lần chạy đầu: dense trả lời 8, từ chối 9 (7 từ chối oan); rerank trả lời 9, từ chối 8. Nguyên nhân (đọc từng trace): model gộp nhiều ID trong một cặp ngoặc `[a, b]`, trong khi khung starter đòi từng `[id]`. Cách thử: prompt yêu cầu mỗi ID một cặp ngoặc và tách marker gộp (không đổi ID hay nội dung). Sau sửa: cả hai trả lời 13, từ chối nhầm còn 2 (`d08`, `d09`) → ghi ở `results/agent/day6-dev-*-marker-bug/` làm số "trước".
- **`d08`/`d09`**: cùng một câu hỏi nhưng đáp án chuẩn khác nhau (13 RCT/15 730 phụ nữ so với 60 RCT/37 720); agent từ chối vì câu mơ hồ. Chấm 0 theo luật script; đây là lỗi benchmark thừa hưởng từ Day 6.
- **Lỗi hình do mô tả vision (`d-im3`, `t-im5`).** Mô tả hình do model vision viết đã xếp sai trạng thái của quốc gia trên bản đồ (Canada "Yes" thay vì "No"; Trung Quốc xuất hiện ở nhiều nhóm). Agent trả lời theo mô tả nên sai. Mô tả hình không tự bảo đảm đúng; chỉ kiểm tay Fig 2.20, các bản đồ khác là rủi ro còn lại.
- **Đánh đổi.** Rerank tốn khoảng 2 lần token và 1,2–1,9 lần thời gian so với dense (WHO test: 426 nghìn so với 186 nghìn token vào, 162 s so với 138 s; Day 6 dev: 198 s so với 104 s) nhưng loại hết từ chối oan (0/24 so với 2/23) và đạt nhiều câu hơn (28/30 so với 26/30). Test Day 6 chỉ có 5 câu có đáp án nên không đủ để tách dense và rerank.
- **Giới hạn.** (1) Nhãn được đọc và gán với sự hỗ trợ của trợ lý AI (Claude): mỗi đáp án được đối chiếu với nội dung các chunk được trích, kèm kiểm tra tự động xem các con số của câu trả lời có nằm trong chunk đó không; sinh viên chịu trách nhiệm xác nhận. (2) `temperature = 0` nhưng model không bảo đảm lặp lại hoàn toàn. (3) Test Day 6 agent đã chạy hai lần (lần đầu bằng Gemini API trực tiếp, lỗi parse ở `t04`), lưu ở `results/agent/superseded-gemini-direct/`; giữa hai lần chỉ sửa trình phân tích rerank. (4) Retrieval WHO đo bằng Gemini API trực tiếp, agent bằng OpenRouter (cùng model). (5) Context chọn theo ngân sách ký tự và khử trùng lặp; chưa thử đoạn lân cận hoặc nén.

## Thử thách nâng cao

- **Tài liệu, nguồn, quyền, số trang, phiên bản.** *World health statistics 2023: Monitoring health for the SDGs* (WHO, ISBN 978-92-4-007432-3), 136 trang, CC BY-NC-SA 3.0 IGO; tải từ https://www.who.int/publications/i/item/9789240074323. Không commit PDF (tái tạo bằng `bonus/extract.py --pdf …`); chỉ đẩy crop/chunk nhỏ phục vụ kiểm chứng.
- **Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index; phần chưa xử lý.** Pipeline ba nhánh gộp thành một index: (1) *text*: PyMuPDF, bỏ đầu trang/số trang; (2) *bảng*: `find_tables` + đọc từng ô (`get_textbox`), bảng annex lẻ mượn tên quốc gia từ trang chẵn đối diện; (3) *hình/biểu đồ*: cắt từ chú thích "Figure x.y" tới dòng "Source:", lấy text layer và mô tả bằng Gemini vision (44 hình, giữ `bbox` và ảnh crop để kiểm chứng). Chunk: 336 text, 156 bảng, 44 hình. Chưa xử lý: các trang trống đã kể; hình chỉ là trang trí không đưa vào câu hỏi.
- **Cách chia benchmark, schema evidence, model, cấu hình đã chốt trên dev.** Mỗi câu có ID, nhóm chính, câu hỏi, đáp án hoặc hành vi từ chối, trang, `chunk_id`, vùng/hàng/cột (`locator`), chuỗi nguyên văn, đơn vị/điều kiện/phép tính. Cấu hình chốt trên dev: agent hybrid + rerank (15 ứng viên), top-k 5, budget 12 000, tối đa 4 lượt (`results/agent/config.lock.json`).

Tiêu chí đạt (đúng theo ADVANCED.md): câu có đáp án chỉ đạt khi trả lời đúng và đủ **và** mọi citation được chấm là hỗ trợ; thiếu evidence đạt khi từ chối, không thêm khẳng định; lỗi hệ thống không đạt, vẫn nằm trong mẫu số.

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | 6/6 | 100% | Gồm phép tính (9,0 năm; 26,5 điểm phần trăm) đều đúng |
| Ảnh, sơ đồ | 4/5 | 80% | `t-im5` (bản đồ khí hậu): trả lời "Yes" nhưng liệt kê thêm Trung Quốc vào "No", "Not a participant", "Not applicable"; mô tả hình sai |
| Biểu đồ | 4/5 | 80% | `t-ch5`: số đúng (32%, 23%, 28%) nhưng thêm hai citation bảng annex không liên quan → không đạt theo luật citation |
| Multi-hop | 4/4 | 100% | Cả hai nửa câu (kể cả Mexico tr. 100 + 101) đều có trong context |
| Text | 4/4 | 100% | |
| Thiếu bằng chứng | 6/6 | 100% | 6/6 từ chối, không thêm khẳng định |
| **Tổng** | **28/30** | **93,3%** | **0 lỗi hệ thống**; cần ≥ 27/30 (90%) |

Baseline dense trên cùng test: **26/30 (86,7%)**, 1 lỗi hệ thống (`t-mh3`: controller trả JSON không hợp lệ), 2 từ chối oan (`t-tb6`, `t-mh1`), chưa đạt ngưỡng.

Chi tiết từng câu test (pass/fail + lý do): `results/agent/whs-test-D-hybrid-rerank/pass_rate.json`; trace và nhãn: `traces.json`, `reviews.json` cùng thư mục. Thời gian: 162 s cho 30 câu (trung vị 4,1 s/câu), 121 lượt gọi API, 425 567 + 12 580 token, chi phí ước tính ≈ $0,16.

**Tái lập.** Cần Docker (PostgreSQL + pgvector), `GEMINI_API_KEY` (embedding) và `OPENROUTER_API_KEY` trong `.env` (không commit). Lệnh: `bonus/extract.py` → `describe_figures.py` → `build_chunks.py` → `index.py` → `eval_retrieval.py --split dev|test` → `src/run_agent_eval.py` → `results/agent/pass_rate.py`; `python -m unittest discover -s tests -v` chạy 34 test (offline, không đo chất lượng model).

## Kết luận và giới hạn

- Rerank là cấu hình tốt nhất trên cả hai corpus (dev: MRR 0,910 và 0,967; test WHO: Hit@3 22/24), và agent dùng nó đạt **28/30 (93,3%)** trên test WHO, vượt ngưỡng 90% của thử thách; dense baseline chưa đạt (86,7%).
- Điểm yếu còn lại: (a) mô tả hình bằng vision có thể sai, đặc biệt bản đồ phân loại; (b) agent đôi khi thêm citation thừa; (c) câu cần nhiều hàng bảng phụ thuộc vào việc cả hai hàng cùng vào top-k; (d) benchmark Day 6 có hai câu mơ hồ (`d08`, `d09`).
- Nguồn: WHO (2011) và WHO (2023) như trên; Gemini API (embedding, vision); OpenRouter (`google/gemini-3.5-flash-lite`). Có dùng trợ lý AI để viết mã và hỗ trợ đọc đối chiếu nhãn; sinh viên chịu trách nhiệm kiểm tra.
