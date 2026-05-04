# Individual Reflection — Lab 18

**Tên:** Vũ Trung Lập  
**Module phụ trách:** M2: Hybrid Search (BM25 + Dense + RRF)

---

## 1. Đóng góp kỹ thuật

- **Module đã implement:** Module 2 - Xây dựng hệ thống tìm kiếm lai (Hybrid Search) kết hợp giữa tìm kiếm từ khóa và tìm kiếm ngữ nghĩa.
- **Các hàm/class chính đã viết:**
  - `segment_vietnamese`: Hàm xử lý tiền xử lý văn bản, chuẩn hóa Unicode NFC và tách từ tiếng Việt.
  - `BM25Search`: Triển khai tìm kiếm Lexical dựa trên thuật toán BM25Okapi.
  - `DenseSearch`: Triển khai tìm kiếm Semantic sử dụng Qdrant Vector Database và Sentence Transformers.
  - `reciprocal_rank_fusion (RRF)`: Thuật toán kết hợp và xếp hạng lại kết quả từ nhiều nguồn tìm kiếm.
  - `HybridSearch`: Class tích hợp toàn bộ quy trình tìm kiếm.
- **Số tests pass:** 5/5 (Hoàn thành 100% yêu cầu của Module 2).

## 2. Kiến thức học được

- **Khái niệm mới nhất:** Reciprocal Rank Fusion (RRF) - một phương pháp cực kỳ hiệu quả để kết hợp các hệ thống xếp hạng khác nhau mà không cần chuẩn hóa điểm số (score normalization).
- **Điều bất ngờ nhất:** Sự không nhất quán của các bộ tách từ (tokenizers) trong tiếng Việt khi đối mặt với các truy vấn ngắn và dài, dẫn đến việc BM25 bị mất kết quả nếu không có chiến lược "Hybrid Tokenization".
- **Kết nối với bài giảng:** Áp dụng trực tiếp kiến thức về Hybrid Retrieval và sự kết hợp giữa Keyword matching (Slide Retrieval) và Vector embeddings.

## 3. Khó khăn & Cách giải quyết

- **Khó khăn lớn nhất:** Lỗi điểm số BM25 bằng 0 mặc dù từ khóa có xuất hiện (do lỗi Unicode NFD và sự không nhất quán của `underthesea`). Ngoài ra còn có vấn đề về môi trường khi server Qdrant không khả dụng.
- **Cách giải quyết:** 
  - Sử dụng `unicodedata.normalize('NFC')` để chuẩn hóa mọi ký tự tiếng Việt.
  - Áp dụng "Hybrid Tokenization": Lưu cả từ ghép (nghỉ_phép) và các từ đơn lẻ (nghỉ, phép) vào index để tăng khả năng tìm thấy (Recall).
  - Thêm cơ chế Fallback: Tự động chuyển sang mode `in-memory` cho Qdrant nếu không kết nối được server.
- **Thời gian debug:** Khoảng 3 giờ cho các vấn đề liên quan đến tokenization và môi trường.

## 4. Nếu làm lại

- **Sẽ làm khác điều gì:** Sẽ tìm hiểu kỹ hơn về các bộ tách từ khác như `ViTokenizer` hoặc `VnCoreNLP` để so sánh độ ổn định với `underthesea`.
- **Module nào muốn thử tiếp:** Module 3 (Reranking) vì đây là bước tối quan trọng để lọc nhiễu sau khi Hybrid Search trả về kết quả thô.

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 5 |
| Code quality | 5 |
| Teamwork | 4 |
| Problem solving | 5 |
