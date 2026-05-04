"""Module 2: Hybrid Search — BM25 (Vietnamese) + Dense + RRF."""

import os, sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, EMBEDDING_MODEL,
                    EMBEDDING_DIM, BM25_TOP_K, DENSE_TOP_K, HYBRID_TOP_K)


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict
    method: str  # "bm25", "dense", "hybrid"


import re
import unicodedata

def segment_vietnamese(text: str) -> str:
    """Tách từ tiếng Việt và chuẩn hóa văn bản (Unicode NFC)."""
    if not text:
        return ""
    # 1. Chuẩn hóa Unicode NFC để tránh lỗi ký tự tổ hợp
    text = unicodedata.normalize('NFC', text)
    # 2. Chuẩn hóa: viết thường và xóa dấu câu cơ bản
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    
    try:
        from underthesea import word_tokenize
        tokenized = word_tokenize(text, format="text")
        # Mẹo: Trả về cả từ ghép (nghỉ_phép) và từ đơn (nghỉ phép) để BM25 luôn khớp
        return tokenized + " " + tokenized.replace("_", " ")
    except (ImportError, Exception):
        return text


class BM25Search:
    def __init__(self):
        self.corpus_tokens = []
        self.documents = []
        self.bm25 = None

    def index(self, chunks: list[dict]) -> None:
        """Xây dựng index BM25 từ các chunk."""
        from rank_bm25 import BM25Okapi
        self.documents = chunks
        self.corpus_tokens = [segment_vietnamese(c["text"]).split() for c in chunks]
        print(f"\n[DEBUG] Index Tokens[0]: {self.corpus_tokens[0]}")
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = BM25_TOP_K) -> list[SearchResult]:
        """Tìm kiếm sử dụng BM25."""
        if not self.bm25:
            return []
        
        tokenized_query = segment_vietnamese(query).split()
        print(f"[DEBUG] Query Tokens: {tokenized_query}")
        
        scores = self.bm25.get_scores(tokenized_query)
        print(f"[DEBUG] Scores: {scores}")
        
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for i in top_indices:
            if scores[i] > 0:
                results.append(SearchResult(
                    text=self.documents[i]["text"],
                    score=float(scores[i]),
                    metadata=self.documents[i]["metadata"],
                    method="bm25"
                ))
        return results


class DenseSearch:
    def __init__(self):
        from qdrant_client import QdrantClient
        try:
            self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            self.client.get_collections()
            print("  ✓ Connected to Qdrant server")
        except Exception:
            print("  ⚠ Qdrant server not available, using in-memory mode")
            self.client = QdrantClient(":memory:")
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(EMBEDDING_MODEL)
        return self._encoder

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        """Lưu các chunk vào Qdrant vector database."""
        from qdrant_client.models import Distance, VectorParams, PointStruct
        
        # Khởi tạo collection
        self.client.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
        )
        
        texts = [c["text"] for c in chunks]
        vectors = self._get_encoder().encode(texts, show_progress_bar=True)
        
        points = [
            PointStruct(
                id=i, 
                vector=v.tolist(), 
                payload={**c["metadata"], "text": c["text"]}
            ) for i, (v, c) in enumerate(zip(vectors, chunks))
        ]
        
        self.client.upsert(collection_name=collection, points=points)

    def search(self, query: str, top_k: int = DENSE_TOP_K, collection: str = COLLECTION_NAME) -> list[SearchResult]:
        """Tìm kiếm sử dụng Dense Vector."""
        from qdrant_client.models import PointStruct
        query_vector = self._get_encoder().encode(query).tolist()
        try:
            hits = self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k
            )
        except AttributeError:
            hits = self.client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=top_k
            ).points

        return [
            SearchResult(
                text=hit.payload["text"],
                score=hit.score,
                metadata=hit.payload,
                method="dense"
            ) for hit in hits
        ]


def reciprocal_rank_fusion(results_list: list[list[SearchResult]], k: int = 60,
                           top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
    """Kết hợp các kết quả xếp hạng bằng thuật toán RRF."""
    rrf_scores = {}  # text -> {"score": float, "result": SearchResult}
    
    for result_list in results_list:
        for rank, result in enumerate(result_list):
            if result.text not in rrf_scores:
                rrf_scores[result.text] = {"score": 0.0, "result": result}
            
            # Công thức RRF: score = sum(1 / (k + rank + 1))
            rrf_scores[result.text]["score"] += 1.0 / (k + rank + 1)
            
    # Sắp xếp theo score giảm dần
    sorted_results = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
    
    final_results = []
    for item in sorted_results[:top_k]:
        res = item["result"]
        final_results.append(SearchResult(
            text=res.text,
            score=item["score"],
            metadata=res.metadata,
            method="hybrid"
        ))
        
    return final_results


class HybridSearch:
    """Combines BM25 + Dense + RRF. (Đã implement sẵn — dùng classes ở trên)"""
    def __init__(self):
        self.bm25 = BM25Search()
        self.dense = DenseSearch()

    def index(self, chunks: list[dict]) -> None:
        self.bm25.index(chunks)
        self.dense.index(chunks)

    def search(self, query: str, top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
        bm25_results = self.bm25.search(query, top_k=BM25_TOP_K)
        try:
            dense_results = self.dense.search(query, top_k=DENSE_TOP_K)
            return reciprocal_rank_fusion([bm25_results, dense_results], top_k=top_k)
        except Exception as e:
            print(f"  ⚠ Dense search failed ({e}), using BM25 only")
            return bm25_results[:top_k]


if __name__ == "__main__":
    print(f"Original:  Nhân viên được nghỉ phép năm")
    print(f"Segmented: {segment_vietnamese('Nhân viên được nghỉ phép năm')}")
