# ADR-001: Tài liệu và pipeline cho thử thách bonus (Day 7)

**Status:** Accepted (tài liệu), Proposed (pipeline, chờ kết quả dev)
**Date:** 2026-11-16
**Deciders:** Trịnh Ngọc Ninh (người làm bài); giảng viên cần xác nhận mục "Rủi ro 1"

## Context
Bonus 15 điểm yêu cầu (ADVANCED.md): một tài liệu thật từ 100 trang có text, bảng, ảnh, biểu đồ; index toàn bộ nội dung hữu ích; test ≥30 câu (≥24 có đáp án: bảng 6, ảnh/sơ đồ 5, biểu đồ 5, multi-hop 4, text 4; ≥6 thiếu bằng chứng); đạt ≥90% (27/30), không cộng một phần.

Đã khảo sát 4 PDF bằng PyMuPDF:

| Tài liệu | Trang | Bảng | Biểu đồ | Ảnh/sơ đồ có nội dung | Kết quả |
|---|---:|---|---|---|---|
| Ethics & governance of AI for health (WHO 2021) | 165 | không | không | 2 sơ đồ | Loại |
| World health statistics 2026 | 67 | có | có | gần như không | Loại (thiếu trang) |
| **World health statistics 2023 (WHO)** | **136** | **34 trang (annex 96–127)** | **46 hình** | bản đồ tô màu, vài sơ đồ | **Chọn** |

## Decision
Dùng **World health statistics 2023: Monitoring health for the SDGs** (WHO, ISBN 978-92-4-007432-3, 136 trang, CC BY-NC-SA 3.0 IGO, tr. 4). File không commit; repo ghi nguồn và cách tải.

Pipeline **đa phương thức theo từng trang** (Option B), dùng lại embedding Day 6 (`gemini-embedding-001`, 768 chiều, pgvector):
1. **Text:** chunk theo đoạn, giữ `page` vật lý.
2. **Bảng:** `find_tables` → markdown; bảng annex dài chia theo nhóm hàng và lặp lại tiêu đề cột; metadata `kind=table`, `bbox`.
3. **Hình/biểu đồ/bản đồ:** cắt vùng từ caption "Figure x.y" đến dòng "Source:", lưu PNG; dùng model thị giác sinh mô tả có số liệu đọc được + trục/chú giải; chunk `kind=figure` gồm caption + text trong hình + mô tả. Ảnh crop dùng để kiểm chứng gold bằng mắt.
4. Mọi chunk có `source_id`, `source`, `page`, `kind`, `bbox`, `crop` (nếu có).

## Options Considered
### Option A: Chỉ text + bảng (không dùng thị giác)
| Dimension | Assessment |
|---|---|
| Complexity | Thấp |
| Cost | Thấp, không gọi model thị giác |
| Chất lượng | Biểu đồ/bản đồ: text layer chỉ có nhãn trục (đã kiểm: tr. 20, 63), **không có giá trị dữ liệu** → fail nhóm biểu đồ |
**Loại:** không thể đạt các nhóm biểu đồ và ảnh/sơ đồ.

### Option B: Chunk đa loại + mô tả thị giác (chọn)
| Dimension | Assessment |
|---|---|
| Complexity | Trung bình |
| Cost | ~46 hình + vài trang đặc biệt = ~60 lượt gọi vision, một lần, cache được |
| Tái lập | Mô tả được lưu thành file, kèm ảnh crop để người chấm đối chiếu |
**Ưu:** dùng lại vector store Day 6; retrieval và agent không đổi. **Nhược:** mô tả do model sinh có thể sai → phải kiểm với ảnh gốc, ghi tỉ lệ sai.

### Option C: Embedding ảnh (multimodal embedding) cho toàn trang
Cost trung bình, nhưng index Day 6 là text-only (768 chiều); đổi model cần index mới và vẫn cần đọc giá trị. **Hoãn:** thử sau nếu B không đạt trên dev.

## Trade-off Analysis
B đánh đổi thêm một bước tiền xử lý để có evidence truy xuất được từ hình. Rủi ro sai số mô tả được kiểm soát bằng ảnh crop và việc gold của câu biểu đồ chỉ gồm giá trị đọc được rõ ràng (nhãn dữ liệu hoặc so sánh thứ hạng/xu hướng chắc chắn).

## Rủi ro
1. **Nhóm "ảnh, sơ đồ" (≥5 câu test):** tài liệu không có ảnh chụp; chỉ có bản đồ tô màu (Fig. 1.2, 1.6, 1.16, 2.2, 2.15, 2.19) và sơ đồ (Fig. 2.20 HIV cascade, Fig. 3.3). **Cần giảng viên xác nhận** chúng được tính là ảnh/sơ đồ. Nếu không, bonus không đạt.
2. Ngưỡng 90%: tối đa 3 câu sai trên 30 câu. Cần chừa ngân sách kiểm tay từng câu.
3. Câu biểu đồ/bản đồ cần đọc giá trị: chỉ dùng giá trị kiểm chứng được trên ảnh gốc.
4. Gửi trang/hình tới API ngoài: nội dung CC BY-NC-SA, công khai; không có dữ liệu cá nhân.

## Consequences
- Dễ hơn: kiểm chứng evidence (có crop, trang, bbox); dùng lại toàn bộ agent/retrieval Day 7.
- Khó hơn: phải duy trì thêm một pha tiền xử lý và nhãn thủ công cho ~48 câu.
- Cần xem lại: nếu mô tả thị giác sai nhiều, thử Option C hoặc OCR số trên hình.

## Action Items
1. [x] Chốt tài liệu, ghi ADR.
2. [ ] `bonus/extract.py`: text, bảng, crop hình, chunk đa loại.
3. [ ] Mô tả hình bằng model thị giác; lưu kèm crop.
4. [ ] Benchmark: dev ≥15+3, test ≥24+6, nhãn nhóm chính, evidence từng câu; đóng băng test.
5. [ ] Hỏi giảng viên về bản đồ/sơ đồ cho nhóm ảnh/sơ đồ.
