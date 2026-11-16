# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Framework (người dùng chọn "Framework" thay vì HTML tĩnh). Lựa chọn cụ thể được giao cho người dựng: **Vite + JavaScript thuần + GSAP**, build ra một file HTML tự chứa (`vite-plugin-singlefile`) để người xem mở trực tiếp bằng trình duyệt, không cần server. Lý do: người xem tự bấm, không có người thuyết minh, nên sản phẩm phải mở được bằng một cú nhấp.

## Users

Người xem tự khám phá deck mà không có người thuyết minh: giảng viên/người chấm lab Day 7 (Agentic RAG) và bạn học mở lại từ repo. Họ đã biết RAG ở mức khái niệm; việc của họ là hiểu pipeline này làm gì với tài liệu thật và kiểm tra rằng kết quả là thật, có thể truy ngược.

## Product Purpose

Một deck trình bày tương tác bằng HTML cho bài cá nhân Day 7 của Trịnh Ngọc Ninh (MSSV 2A202603996). Deck trực quan hóa cách một báo cáo 136 trang được index và truy xuất, và để người xem tự thao tác với dữ liệu thật của pipeline. Thành công = người xem hiểu được đường đi của dữ liệu và tự kiểm chứng được một bằng chứng mà không cần ai giải thích.

## Positioning

Mọi thứ trên deck là đầu ra thật của pipeline trong repo này (chunk, ảnh crop, mô tả hình, câu hỏi benchmark, trace truy xuất), không phải sơ đồ minh họa chung về RAG.

## Operating Context

- Tài liệu nguồn: WHO, *World health statistics 2023: Monitoring health for the SDGs* (136 trang, CC BY-NC-SA 3.0 IGO).
- Phạm vi deck: toàn bộ bài Day 7. Các slide đầu là pipeline index; sau đó là benchmark, 6 phương pháp retrieval, agent/citation/abstention và phân tích lỗi.
- Pipeline index: 3 nhánh theo loại dữ liệu (text, bảng, hình) gộp về **một** index chung (pgvector, `gemini-embedding-001`, 768 chiều).
- Benchmark: 48 câu (dev 15 + 3, test 24 + 6) theo 5 nhóm + câu thiếu bằng chứng.
- Sáu phương pháp retrieval: dense, BM25, hybrid RRF, rerank, viết lại query, multi-stage.
- Ngôn ngữ giao diện: tiếng Việt; thuật ngữ kỹ thuật và trích dẫn từ tài liệu giữ nguyên tiếng Anh.

## Capabilities and Constraints

- Deck chạy offline từ một file; dữ liệu được nhúng lúc build từ `bonus/data` và `bonus/results`.
- Không bịa số liệu (RULES.md của lab). Phần chưa đo phải hiện rõ là chưa có dữ liệu, không điền số giả.
- Không làm lộ đáp án chuẩn của bộ **test** trước khi chốt cấu hình: deck chỉ dùng câu hỏi và trace của **dev**.
- Chưa có tại thời điểm viết: kết quả đo 6 phương pháp, agent trả lời, kết quả test. Đây là các quyết định/dữ liệu còn mở.

## Evidence on Hand

- `bonus/data/chunks.json` (536 chunk: 336 text, 156 bảng, 44 hình), `bonus/data/figures.json`, `bonus/data/crops/*.png` (44 ảnh crop hình).
- `bonus/data/figure_descriptions.json` (mô tả do model thị giác sinh; đang hoàn tất).
- `bonus/data/questions.json` (48 câu, evidence đã kiểm), `bonus/data/extract_report.json`, `bonus/data/benchmark_report.json`.
- `docs/ADR-001-bonus-document-and-pipeline.md` (quyết định tài liệu và pipeline).
- Chưa có: `bonus/results/dev-summary.json` (kết quả 6 phương pháp), trace agent. Không được tự tạo.

## Product Principles

1. Bằng chứng trước lời khẳng định: mỗi con số trên deck trỏ được về trang, chunk hoặc ảnh crop gốc.
2. Trung thực về trạng thái: phần chưa làm nói rõ là chưa làm.
3. Tự giải thích: người xem không có người thuyết minh vẫn đi hết được.
4. Người xem được chạm vào dữ liệu thật, không chỉ xem hoạt ảnh.
