"""
Module 5: Enrichment Pipeline
==============================
Làm giàu chunks TRƯỚC khi embed: Summarize, HyQA, Contextual Prepend, Auto Metadata.

Test: pytest tests/test_m5.py
"""

import os, sys, asyncio
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY


@dataclass
class EnrichedChunk:
    """Chunk đã được làm giàu."""
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str  # "contextual", "summary", "hyqa", "full"


# ─── Technique 1: Chunk Summarization ────────────────────


async def summarize_chunk(text: str) -> str:
    """
    Tạo summary ngắn cho chunk.
    Embed summary thay vì (hoặc cùng với) raw chunk → giảm noise.

    Args:
        text: Raw chunk text.

    Returns:
        Summary string (2-3 câu).
    """
    if not OPENAI_API_KEY:
        sentences = text.split(". ")
        return ". ".join(sentences[:2]) + "." if len(sentences) > 1 else text

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tóm tắt đoạn văn sau trong 2-3 câu ngắn gọn bằng tiếng Việt."},
                {"role": "user", "content": text},
            ],
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in summarize_chunk: {e}")
        return text[:200] + "..."


# ─── Technique 2: Hypothesis Question-Answer (HyQA) ─────


async def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """
    Generate câu hỏi mà chunk có thể trả lời.
    Index cả questions lẫn chunk → query match tốt hơn (bridge vocabulary gap).

    Args:
        text: Raw chunk text.
        n_questions: Số câu hỏi cần generate.

    Returns:
        List of question strings.
    """
    if not OPENAI_API_KEY:
        return []

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Dựa trên đoạn văn, tạo {n_questions} câu hỏi mà đoạn văn có thể trả lời. Trả về mỗi câu hỏi trên 1 dòng."},
                {"role": "user", "content": text},
            ],
            max_tokens=200,
        )
        questions = resp.choices[0].message.content.strip().split("\n")
        return [q.strip().lstrip("0123456789.-) ") for q in questions if q.strip()]
    except Exception as e:
        print(f"Error in generate_hypothesis_questions: {e}")
        return []


# ─── Technique 3: Contextual Prepend (Anthropic style) ──


async def contextual_prepend(text: str, document_title: str = "") -> str:
    """
    Prepend context giải thích chunk nằm ở đâu trong document.
    Anthropic benchmark: giảm 49% retrieval failure (alone).

    Args:
        text: Raw chunk text.
        document_title: Tên document gốc.

    Returns:
        Text với context prepended.
    """
    if not OPENAI_API_KEY:
        return text

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Viết 1 câu ngắn mô tả đoạn văn này nằm ở đâu trong tài liệu và nói về chủ đề gì. Chỉ trả về 1 câu."},
                {"role": "user", "content": f"Tài liệu: {document_title}\n\nĐoạn văn:\n{text}"},
            ],
            max_tokens=80,
        )
        context = resp.choices[0].message.content.strip()
        return f"{context}\n\n{text}"
    except Exception as e:
        print(f"Error in contextual_prepend: {e}")
        return text


# ─── Technique 4: Auto Metadata Extraction ──────────────


async def extract_metadata(text: str) -> dict:
    """
    LLM extract metadata tự động: topic, entities, date_range, category.

    Args:
        text: Raw chunk text.

    Returns:
        Dict with extracted metadata fields.
    """
    if not OPENAI_API_KEY:
        return {}

    try:
        import json
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 'Trích xuất metadata từ đoạn văn. Trả về định dạng JSON duy nhất với các field: {"topic": "...", "entities": ["..."], "category": "policy|hr|it|finance", "language": "vi|en"}'},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            max_tokens=150,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"Error in extract_metadata: {e}")
        return {}


# ─── Full Enrichment Pipeline (Async/Parallel) ─────────


async def enrich_single_chunk(
    chunk: dict,
    methods: list[str],
    semaphore: asyncio.Semaphore,
) -> EnrichedChunk:
    """Enrich single chunk with all techniques in parallel."""
    async with semaphore:
        text = chunk["text"]
        meta = chunk["metadata"]

        tasks = []

        if "summary" in methods or "full" in methods:
            tasks.append(summarize_chunk(text))
        else:
            tasks.append(asyncio.sleep(0, ""))

        if "hyqa" in methods or "full" in methods:
            tasks.append(generate_hypothesis_questions(text))
        else:
            tasks.append(asyncio.sleep(0, []))

        if "contextual" in methods or "full" in methods:
            tasks.append(contextual_prepend(text, meta.get("source", "")))
        else:
            tasks.append(asyncio.sleep(0, text))

        if "metadata" in methods or "full" in methods:
            tasks.append(extract_metadata(text))
        else:
            tasks.append(asyncio.sleep(0, {}))

        summary, questions, enriched_text, auto_meta = await asyncio.gather(*tasks)

        return EnrichedChunk(
            original_text=text,
            enriched_text=enriched_text,
            summary=summary,
            hypothesis_questions=questions,
            auto_metadata={**meta, **auto_meta},
            method="+".join(methods),
        )


async def enrich_chunks_async(
    chunks: list[dict],
    methods: list[str] | None = None,
    max_concurrent: int = 5,
) -> list[EnrichedChunk]:
    """
    Async enrichment with parallel requests.
    max_concurrent: Limit concurrent API calls to avoid rate limiting (default 5).

    Args:
        chunks: List of {"text": str, "metadata": dict}
        methods: List of methods to apply. Default: ["contextual", "hyqa", "metadata"]
        max_concurrent: Max concurrent chunks being processed

    Returns:
        List of EnrichedChunk objects.
    """
    if methods is None:
        methods = ["contextual", "hyqa", "metadata"]

    semaphore = asyncio.Semaphore(max_concurrent)

    try:
        from tqdm.asyncio import tqdm
        tasks = [enrich_single_chunk(chunk, methods, semaphore) for chunk in chunks]
        enriched_list = await tqdm.gather(*tasks, desc="Enriching chunks")
    except ImportError:
        tasks = [enrich_single_chunk(chunk, methods, semaphore) for chunk in chunks]
        enriched_list = await asyncio.gather(*tasks)

    return enriched_list


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
    use_async: bool = True,
) -> list[EnrichedChunk]:
    """
    Chạy enrichment pipeline trên danh sách chunks.
    Default: async with parallelization. Fallback to sync if needed.

    Args:
        chunks: List of {"text": str, "metadata": dict}
        methods: List of methods to apply. Default: ["contextual", "hyqa", "metadata"]
        use_async: Use async/parallel (default True)

    Returns:
        List of EnrichedChunk objects.
    """
    if methods is None:
        methods = ["contextual", "hyqa", "metadata"]

    if use_async:
        try:
            return asyncio.run(enrich_chunks_async(chunks, methods))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(enrich_chunks_async(chunks, methods))
    else:
        enriched_list = []
        from tqdm import tqdm
        for chunk in tqdm(chunks, desc="Enriching chunks"):
            text = chunk["text"]
            meta = chunk["metadata"]

            summary = ""
            if "summary" in methods or "full" in methods:
                summary = asyncio.run(summarize_chunk(text))

            questions = []
            if "hyqa" in methods or "full" in methods:
                questions = asyncio.run(generate_hypothesis_questions(text))

            enriched_text = text
            if "contextual" in methods or "full" in methods:
                enriched_text = asyncio.run(contextual_prepend(text, meta.get("source", "")))

            auto_meta = {}
            if "metadata" in methods or "full" in methods:
                auto_meta = asyncio.run(extract_metadata(text))

            enriched_list.append(EnrichedChunk(
                original_text=text,
                enriched_text=enriched_text,
                summary=summary,
                hypothesis_questions=questions,
                auto_metadata={**meta, **auto_meta},
                method="+".join(methods),
            ))

        return enriched_list


# ─── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    sample = "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm. Số ngày nghỉ phép tăng thêm 1 ngày cho mỗi 5 năm thâm niên công tác."

    print("=== Enrichment Pipeline Demo ===\n")
    print(f"Original: {sample}\n")

    s = asyncio.run(summarize_chunk(sample))
    print(f"Summary: {s}\n")

    qs = asyncio.run(generate_hypothesis_questions(sample))
    print(f"HyQA questions: {qs}\n")

    ctx = asyncio.run(contextual_prepend(sample, "Sổ tay nhân viên VinUni 2024"))
    print(f"Contextual: {ctx}\n")

    meta = asyncio.run(extract_metadata(sample))
    print(f"Auto metadata: {meta}")
