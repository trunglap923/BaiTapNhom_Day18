# Individual Reflection — Lab 18

**Tên:** Tạ Vĩnh Phúc  
**Module phụ trách:** M3 (Reranking)

---

## 1. Đóng góp kỹ thuật

- Module đã implement: M3 - Reranking (Áp dụng mô hình CrossEncoder)
- Các hàm/class chính đã viết: 
  - `CrossEncoderReranker`: Load mô hình `BAAI/bge-reranker-v2-m3` và thực hiện hàm `rerank()` để tính điểm tương quan (predict scores) giữa cặp query-doc, sau đó sắp xếp lấy ra top-k `RerankResult`.
  - `FlashrankReranker`: Tích hợp giải pháp thay thế siêu nhẹ với fallback an toàn (graceful degradation) trong trường hợp không cài đặt được thư viện `flashrank`.
  - `benchmark_reranker()`: Hàm tính latency (min, max, avg) của reranker sau nhiều lần chạy qua `time.perf_counter()`.
- Số tests pass: 5/5

## 2. Kiến thức học được

- Khái niệm mới nhất: Hiểu rõ sự khác biệt bản chất giữa Bi-encoder (truy xuất nhanh bằng cosine similarity nhưng kém về ngữ nghĩa chéo) và CrossEncoder (chậm nhưng chấm điểm tương quan ngữ cảnh và câu hỏi cực kì chính xác cho tiếng Việt).
- Điều bất ngờ nhất: Mô hình CrossEncoder có dung lượng khá lớn (lên đến >1GB), lần tải đầu tiên ngốn rất nhiều thời gian và cần cấp phát bộ nhớ RAM/VRAM khá cẩn thận.
- Kết nối với bài giảng (slide nào): Kết nối chặt chẽ với phần "RAG Evaluation & Optimization" — chiến lược Retrieve top-20 bằng Dense Search/BM25 rồi Rerank lại lấy top-3 để đảm bảo input context gửi lên LLM vừa đủ gọn mà vừa chuẩn xác.

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: Tải mô hình `BAAI/bge-reranker-v2-m3` nặng khiến lần đầu khởi chạy mất thời gian. Yêu cầu xử lý an toàn cho module optional `flashrank` để không làm sập pipeline nếu thư viện lỗi.
- Cách giải quyết: Sử dụng cấu trúc Singleton (`_load_model()`) để đảm bảo model nặng chỉ được nạp lên RAM đúng 1 lần duy nhất trong suốt vòng đời của app. Sử dụng `try-except ImportError` cho flashrank để fallback về việc sắp xếp theo điểm score gốc.
- Thời gian debug: 45 phút.

## 4. Nếu làm lại

- Sẽ làm khác điều gì: Mình sẽ viết thêm phần hỗ trợ gọi API của Cohere (`cohere.rerank`) để thay thế model chạy local, nhằm giảm tải phần cứng cho máy và so sánh xem API có cải thiện latency so với chạy BAAI local hay không.
- Module nào muốn thử tiếp: Mình rất tò mò về M5 (Enrichment Pipeline), vì kỹ thuật dùng LLM để chèn thêm ngữ cảnh vào văn bản trước khi embed (Contextual Prepend) hay sinh câu hỏi ảo (HyQA) nghe rất hứa hẹn để giải quyết bài toán lệch từ vựng (vocabulary gap) từ gốc rễ.

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 5 |
| Code quality | 5 |
| Teamwork | 5 |
| Problem solving | 5 |
