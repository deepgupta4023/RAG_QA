from __future__ import annotations

from typing import Any


def build_context_block(retrieved_chunks: list[dict[str, Any]]) -> str:
    """
    Build a readable context block from retrieved chunks.
    """
    blocks: list[str] = []

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        section = chunk.get("section") or "UNKNOWN"
        page_start = chunk.get("page_start")
        page_end = chunk.get("page_end")
        text = (chunk.get("text") or "").strip()

        blocks.append(
            "\n".join(
                [
                    f"[Source {idx}]",
                    f"Section: {section}",
                    f"Pages: {page_start} -> {page_end}",
                    "Content:",
                    text,
                ]
            )
        )

    return "\n\n".join(blocks).strip()


def build_answer_prompt(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    """
    Build a grounded QA prompt using retrieved chunk context.
    """
    context_block = build_context_block(retrieved_chunks)

    return f"""
You are answering questions about a single PDF document.

Instructions:
- Answer only from the provided context.
- Do not invent facts, numbers, dates, or names.
- If the context is insufficient, say that the answer is not clearly supported by the provided excerpts.
- Prefer a concise answer.
- If possible, base the answer on the most relevant sources.
- Do not mention anything outside the provided context.

Question:
{question}

Context:
{context_block}

Return:
- A short answer paragraph.
""".strip()