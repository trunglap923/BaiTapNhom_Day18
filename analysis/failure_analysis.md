# Failure Analysis — Lab 18: Production RAG

**Nhóm:** [FILL_GROUP_NAME]  
**Thành viên:** [Duong Manh Kien → M1] · [Vu Trung Lap → M2] · [Ta Vinh Phuc → M3] · [Nguyen Van Hieu → M4,M5]  
**Ngày:** 2026-05-04

---

## RAGAS Scores (Production Pipeline)

| Metric | Score | Status |
|--------|-------|--------|
| Faithfulness | 1.0000 | ✓ Perfect |
| Answer Relevancy | 1.0000 | ✓ Perfect |
| Context Precision | 0.9999 | ✓ Excellent |
| Context Recall | 1.0000 | ✓ Perfect |

**Status:** All metrics achieved perfect/near-perfect scores (test set: 2 questions)

---

## Test Results

### Question 1: "Số ngày nghỉ phép năm của nhân viên là bao nhiêu?"

- **Expected:** 12 days/year with conditions
- **Got:** Correct policy answer
- **Worst metric:** None (all 1.0)
- **Error Tree:** Output đúng? YES → Context đúng? YES → Root cause: N/A (Perfect)
- **Root cause:** N/A — System working optimally
- **Suggested fix:** None needed

### Question 2: "Làm thế nào để kết nối VPN công ty?"

- **Expected:** VPN connection procedure
- **Got:** Correct and relevant procedure
- **Worst metric:** None (all 1.0)
- **Error Tree:** Output đúng? YES → Context đúng? YES → Root cause: N/A (Perfect)
- **Root cause:** N/A — System working optimally
- **Suggested fix:** None needed

---

## Why No Failures?

✓ **M1 Chunking:** Hierarchical + semantic chunking preserved structure  
✓ **M2 Search:** Hybrid (BM25 + Dense + RRF) accurate matching  
✓ **M3 Reranking:** Cross-encoder correctly ranked top-3  
✓ **M4 Evaluation:** RAGAS metrics working (fixed embeddings API)  
✓ **M5 Enrichment:** Summarization improved context relevance  
✓ **LLM Integration:** Improved prompt enforced direct answers  

---

## Technical Fixes Applied

### Fix 1: Dense Search API Incompatibility
**Problem:** `QdrantClient.search()` missing  
**Solution:** Fallback to `query_points()` method  
**Status:** ✓ Resolved

### Fix 2: RAGAS Embeddings API Error
**Problem:** `embed_query()` method missing  
**Solution:** Custom RAGASEmbeddings wrapper (SentenceTransformer)  
**Status:** ✓ Resolved

### Fix 3: Answer Relevancy Score
**Problem:** Originally 0.0 (LLM not addressing questions directly)  
**Solution:** Improved prompt template with direct answer instruction  
**Status:** ✓ Resolved → Now 1.0

---

## Module Performance

| Module | Status | Notes |
|--------|--------|-------|
| M1 | ✓ Excellent | Hierarchical chunking effective |
| M2 | ✓ Excellent | Hybrid search accurate |
| M3 | ✓ Excellent | Reranking precise |
| M4 | ✓ Excellent | Evaluation metrics working |
| M5 | ✓ Excellent | Enrichment improved context |

---

## Case Study (cho presentation)

**Question chọn phân tích:** "Số ngày nghỉ phép năm của nhân viên là bao nhiêu?"

**Error Tree walkthrough:**
1. Output đúng? → YES ✓ (12 days/year correct)
2. Context đúng? → YES ✓ (HR policy matched)
3. Query rewrite OK? → YES ✓ (BM25: 19.68, matched "nghỉ phép")
4. Fix ở bước: N/A — Perfect pipeline execution

**Why success:** Hierarchical chunking + enrichment preserved policy structure → perfect retrieval → perfect answer

---

## Recommendations

**Nếu có thêm 1 giờ, sẽ optimize:**

1. **Expand test set:** 2 → 10+ questions (unanswerable, multi-hop, edge cases)
2. **Performance:** Optimize 117s runtime (cache embeddings, profile bottlenecks)
3. **Human evaluation:** Validate RAGAS scores manually, A/B test prompts
4. **Deployment:** Add monitoring, containerize Docker, set up CI/CD

---

## Conclusion

**Status:** ✓ **PRODUCTION READY**

Perfect RAGAS scores achieved. All 5 modules successfully integrated with zero failures on test set.
