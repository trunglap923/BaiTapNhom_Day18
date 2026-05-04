# Individual Reflection — Lab 18

**Tên:** Nguyễn Văn Hiếu
**Module phụ trách:** M4 (Evaluation) & M5 (Enrichment)

---

## 1. Đóng góp kỹ thuật

- Module đã implement: M4 (RAGAS Evaluation) và M5 (Enrichment Pipeline).
- Các hàm/class chính đã viết: 
    - `evaluate_ragas`, `failure_analysis` (M4).
    - `summarize_chunk`, `generate_hypothesis_questions`, `contextual_prepend`, `extract_metadata`, `enrich_chunks` (M5).
- Số tests pass: 8/8 (4 tests M4, 4 tests M5).

## 2. Kiến thức học được

- Khái niệm mới nhất: Hiểu sâu về 4 chỉ số của RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall) và kỹ thuật "Contextual Prepend" của Anthropic để cải thiện retrieval hiệu quả.
- Điều bất ngờ nhất: Việc làm giàu dữ liệu (Enrichment) bằng cách sinh câu hỏi giả định (HyQA) có thể giúp thu hẹp "vocabulary gap" giữa câu hỏi của người dùng và nội dung tài liệu.
- Kết nối với bài giảng: Áp dụng trực tiếp lý thuyết về Production RAG, RAG Evaluation và Advanced Indexing trong slide bài học ngày 18.

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: Thư viện Ragas cập nhật phiên bản (v0.2+) gây ra lỗi tương thích về tên cột (question -> user_input) và kiểu dữ liệu trả về (float -> list), dẫn đến lỗi `KeyError` và `AssertionError`.
- Cách giải quyết: Đọc kỹ log lỗi và cấu trúc DataFrame trả về của Ragas, viết hàm `get_score` để bóc tách dữ liệu linh hoạt và sử dụng `np.nan_to_num` để xử lý các giá trị không hợp lệ.
- Thời gian debug: Khoảng 1 giờ tập trung xử lý các vấn đề về phiên bản thư viện.

## 4. Nếu làm lại

- Sẽ làm khác điều gì: Sẽ thử nghiệm thêm việc kết hợp Metadata Filter vào quá trình Evaluation để xem độ chính xác có tăng lên rõ rệt không.
- Module nào muốn thử tiếp: Module 2 (Hybrid Search) để nghiên cứu sâu về cách tối ưu trọng số RRF khi kết hợp tìm kiếm ngữ nghĩa và tìm kiếm từ khóa.

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 5 |
| Code quality | 5 |
| Teamwork | 5 |
| Problem solving | 5 |
