"""
Module 1: Advanced Chunking Strategies
=======================================
Implement semantic, hierarchical, và structure-aware chunking.
So sánh với basic chunking (baseline) để thấy improvement.

Test: pytest tests/test_m1.py
"""

import os, sys, glob, re
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_DIR, HIERARCHICAL_PARENT_SIZE, HIERARCHICAL_CHILD_SIZE,
                    SEMANTIC_THRESHOLD)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    parent_id: str | None = None


def load_documents(data_dir: str = DATA_DIR) -> list[dict]:
    """Load all markdown/text files from data/. (Đã implement sẵn)"""
    docs = []
    for fp in sorted(glob.glob(os.path.join(data_dir, "*.md"))):
        with open(fp, encoding="utf-8") as f:
            docs.append({"text": f.read(), "metadata": {"source": os.path.basename(fp)}})
    return docs


# ─── Baseline: Basic Chunking (để so sánh) ──────────────


def chunk_basic(text: str, chunk_size: int = 500, metadata: dict | None = None) -> list[Chunk]:
    """
    Basic chunking: split theo paragraph (\\n\\n).
    Đây là baseline — KHÔNG phải mục tiêu của module này.
    (Đã implement sẵn)
    """
    metadata = metadata or {}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for i, para in enumerate(paragraphs):
        if len(current) + len(para) > chunk_size and current:
            chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
            current = ""
        current += para + "\n\n"
    if current.strip():
        chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
    return chunks


# ─── Strategy 1: Semantic Chunking ───────────────────────


def chunk_semantic(text: str, threshold: float = SEMANTIC_THRESHOLD,
                   metadata: dict | None = None) -> list[Chunk]:
    """
    Split text by sentence similarity — nhóm câu cùng chủ đề.
    Tốt hơn basic vì không cắt giữa ý.

    Args:
        text: Input text.
        threshold: Cosine similarity threshold. Dưới threshold → tách chunk mới.
        metadata: Metadata gắn vào mỗi chunk.

    Returns:
        List of Chunk objects grouped by semantic similarity.
    """
    metadata = metadata or {}

    # 1. Split text into sentences
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n\n', text) if s.strip()]
    if not sentences:
        return []

    # 2. Encode sentences
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(sentences)

    # 3. Define cosine similarity
    from numpy import dot
    from numpy.linalg import norm
    def cosine_sim(a, b):
        return dot(a, b) / (norm(a) * norm(b) + 1e-8)

    # 4. Group sentences by similarity
    chunks = []
    current_group = [sentences[0]]
    for i in range(1, len(sentences)):
        sim = cosine_sim(embeddings[i-1], embeddings[i])
        if sim < threshold:
            chunk_text = " ".join(current_group).strip()
            chunks.append(Chunk(
                text=chunk_text,
                metadata={**metadata, "chunk_index": len(chunks), "strategy": "semantic"}
            ))
            current_group = [sentences[i]]
        else:
            current_group.append(sentences[i])

    # Don't forget last group
    if current_group:
        chunk_text = " ".join(current_group).strip()
        chunks.append(Chunk(
            text=chunk_text,
            metadata={**metadata, "chunk_index": len(chunks), "strategy": "semantic"}
        ))

    return chunks


# ─── Strategy 2: Hierarchical Chunking ──────────────────


def chunk_hierarchical(text: str, parent_size: int = HIERARCHICAL_PARENT_SIZE,
                       child_size: int = HIERARCHICAL_CHILD_SIZE,
                       metadata: dict | None = None) -> tuple[list[Chunk], list[Chunk]]:
    """
    Parent-child hierarchy: retrieve child (precision) → return parent (context).
    Đây là default recommendation cho production RAG.

    Args:
        text: Input text.
        parent_size: Chars per parent chunk.
        child_size: Chars per child chunk.
        metadata: Metadata gắn vào mỗi chunk.

    Returns:
        (parents, children) — mỗi child có parent_id link đến parent.
    """
    metadata = metadata or {}

    # 1. Split text into parents
    paragraphs = text.split("\n\n")
    parents = []
    children = []
    parent_idx = 0

    current_parent = ""
    for para in paragraphs:
        if len(current_parent) + len(para) > parent_size and current_parent:
            # Save current parent
            pid = f"parent_{parent_idx}"
            parent_chunk = Chunk(
                text=current_parent.strip(),
                metadata={**metadata, "chunk_type": "parent", "parent_id": pid}
            )
            parents.append(parent_chunk)

            # Split this parent into children
            children.extend(_split_parent_into_children(current_parent, pid, child_size, metadata))

            current_parent = para + "\n\n"
            parent_idx += 1
        else:
            current_parent += para + "\n\n"

    # Don't forget last parent
    if current_parent.strip():
        pid = f"parent_{parent_idx}"
        parent_chunk = Chunk(
            text=current_parent.strip(),
            metadata={**metadata, "chunk_type": "parent", "parent_id": pid}
        )
        parents.append(parent_chunk)
        children.extend(_split_parent_into_children(current_parent, pid, child_size, metadata))

    return parents, children


def _split_parent_into_children(parent_text: str, parent_id: str, child_size: int, metadata: dict) -> list[Chunk]:
    """Helper: split parent text into children with sliding window."""
    children = []
    text = parent_text.strip()

    for i in range(0, len(text), child_size):
        child_text = text[i:i + child_size]
        if child_text.strip():
            children.append(Chunk(
                text=child_text,
                metadata={**metadata, "chunk_type": "child"},
                parent_id=parent_id
            ))

    return children


# ─── Strategy 3: Structure-Aware Chunking ────────────────


def chunk_structure_aware(text: str, metadata: dict | None = None) -> list[Chunk]:
    """
    Parse markdown headers → chunk theo logical structure.
    Giữ nguyên tables, code blocks, lists — không cắt giữa chừng.

    Args:
        text: Markdown text.
        metadata: Metadata gắn vào mỗi chunk.

    Returns:
        List of Chunk objects, mỗi chunk = 1 section (header + content).
    """
    metadata = metadata or {}

    # 1. Split by markdown headers (# ## ###)
    sections = re.split(r'(^#{1,3}\s+.+$)', text, flags=re.MULTILINE)

    # 2. Pair headers with their content
    chunks = []
    current_header = ""
    current_content = ""

    for part in sections:
        if re.match(r'^#{1,3}\s+', part):
            # This is a header
            if current_content.strip() and current_header:
                chunk_text = f"{current_header}\n{current_content}".strip()
                chunks.append(Chunk(
                    text=chunk_text,
                    metadata={**metadata, "section": current_header, "strategy": "structure"}
                ))
            current_header = part.strip()
            current_content = ""
        else:
            # This is content
            current_content += part

    # Don't forget last section
    if current_content.strip() and current_header:
        chunk_text = f"{current_header}\n{current_content}".strip()
        chunks.append(Chunk(
            text=chunk_text,
            metadata={**metadata, "section": current_header, "strategy": "structure"}
        ))

    return chunks


# ─── A/B Test: Compare All Strategies ────────────────────


def compare_strategies(documents: list[dict]) -> dict:
    """
    Run all strategies on documents and compare.

    Returns:
        {"basic": {...}, "semantic": {...}, "hierarchical": {...}, "structure": {...}}
    """
    results = {}

    for strategy_name, strategy_func in [
        ("basic", lambda t, m: chunk_basic(t, metadata=m)),
        ("semantic", lambda t, m: chunk_semantic(t, metadata=m)),
        ("hierarchical", lambda t, m: chunk_hierarchical(t, metadata=m)),
        ("structure", lambda t, m: chunk_structure_aware(t, metadata=m))
    ]:
        all_chunks = []

        for doc in documents:
            text = doc.get("text", "")
            doc_meta = doc.get("metadata", {})

            if strategy_name == "hierarchical":
                parents, children = strategy_func(text, doc_meta)
                all_chunks.extend(parents)
                all_chunks.extend(children)
            else:
                chunks = strategy_func(text, doc_meta)
                all_chunks.extend(chunks)

        # Calculate stats
        if all_chunks:
            lengths = [len(c.text) for c in all_chunks]
            stats = {
                "num_chunks": len(all_chunks),
                "avg_length": sum(lengths) / len(lengths),
                "min_length": min(lengths),
                "max_length": max(lengths),
                "total_chars": sum(lengths)
            }
        else:
            stats = {
                "num_chunks": 0,
                "avg_length": 0,
                "min_length": 0,
                "max_length": 0,
                "total_chars": 0
            }

        results[strategy_name] = stats

    # Print comparison table
    print("\n" + "=" * 70)
    print(f"{'Strategy':<15} {'Chunks':<10} {'Avg Len':<12} {'Min':<10} {'Max':<10}")
    print("=" * 70)
    for name, stats in results.items():
        print(f"{name:<15} {stats['num_chunks']:<10} "
              f"{stats['avg_length']:<12.0f} {stats['min_length']:<10} {stats['max_length']:<10}")
    print("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    docs = load_documents()
    print(f"Loaded {len(docs)} documents")
    results = compare_strategies(docs)
    for name, stats in results.items():
        print(f"  {name}: {stats}")
