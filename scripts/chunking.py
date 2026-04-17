import json
import re
from pathlib import Path
from typing import Any


ALL_CAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9&,\-()/.' ]{3,}$")


def is_heading(line: str) -> bool:
    """
    Treat strong all-caps lines as section headings.

    Examples:
    - OUR PRIORITIES
    - OUR RESPONSIBILITY
    - SHARE REPURCHASES AND DIVIDENDS
    """
    line = line.strip()
    if not line:
        return False

    # Avoid treating short tokens or numbers as headings
    if len(line) < 4:
        return False
    if line.isdigit():
        return False

    return bool(ALL_CAPS_HEADING_RE.fullmatch(line))


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_paragraphs(text: str) -> list[str]:
    """
    Split cleaned page text into paragraph-like blocks.
    Double newlines define paragraph boundaries.
    """
    text = normalize_whitespace(text)
    if not text:
        return []

    parts = [p.strip() for p in text.split("\n\n")]
    return [p for p in parts if p]


def estimate_word_count(text: str) -> int:
    return len(text.split())


def build_overlap_text(paragraphs: list[dict[str, Any]], overlap_words: int) -> tuple[list[dict[str, Any]], int | None]:
    """
    Build overlap from the tail of previous chunk paragraphs.

    Returns:
    - overlap paragraphs
    - page_start for the overlap block
    """
    if overlap_words <= 0 or not paragraphs:
        return [], None

    selected: list[dict[str, Any]] = []
    total = 0

    for para in reversed(paragraphs):
        selected.append(para)
        total += para["word_count"]
        if total >= overlap_words:
            break

    selected.reverse()
    page_start = selected[0]["page"] if selected else None
    return selected, page_start


def flush_chunk(
    chunks: list[dict[str, Any]],
    chunk_paragraphs: list[dict[str, Any]],
    current_section: str,
    chunk_counter: int,
) -> int:
    """
    Convert accumulated paragraph records into one chunk.

    Skip heading-only chunks, because they add retrieval noise and
    should instead be carried into the next content-bearing chunk.
    """
    if not chunk_paragraphs:
        return chunk_counter

    # Do not emit heading-only chunks
    if is_heading_only_chunk(chunk_paragraphs):
        return chunk_counter

    text = "\n\n".join(p["text"] for p in chunk_paragraphs).strip()
    if not text:
        return chunk_counter

    page_start = chunk_paragraphs[0]["page"]
    page_end = chunk_paragraphs[-1]["page"]

    chunks.append(
        {
            "chunk_id": f"chunk_{chunk_counter:04d}", #04d to ensure the id is atleast 4 digit long, padded by preceding zeros
            "page_start": page_start,
            "page_end": page_end,
            "section": current_section,
            "text": text,
            "word_count": estimate_word_count(text),
        }
    )

    return chunk_counter + 1

def build_chunks(
    pages: list[dict[str, Any]],
    target_words: int = 350,
    overlap_words: int = 60,
) -> list[dict[str, Any]]:
    """
    Build section-aware chunks from extracted page records.

    Behavior:
    - detects all-caps headings as section markers
    - treats a new heading as a hard chunk boundary
    - keeps page_start and page_end correct
    - uses paragraph-based overlap
    """
    chunks: list[dict[str, Any]] = []
    chunk_counter = 1

    current_section = "UNKNOWN"
    chunk_paragraphs: list[dict[str, Any]] = []
    current_word_count = 0

    for page_record in pages:
        page_num = page_record["page"]
        page_text = page_record.get("text", "") or ""
        paragraphs = split_into_paragraphs(page_text)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If this paragraph is an all-caps heading, treat it as a hard boundary.
            if is_heading(para):
                # If current chunk is only a previous heading, don't flush it;
                # just replace it with the new heading.
                if chunk_paragraphs and is_heading_only_chunk(chunk_paragraphs):
                    chunk_paragraphs = []
                    current_word_count = 0
                else:
                    chunk_counter = flush_chunk(
                        chunks=chunks,
                        chunk_paragraphs=chunk_paragraphs,
                        current_section=current_section,
                        chunk_counter=chunk_counter,
                    )
                    chunk_paragraphs = []
                    current_word_count = 0

                current_section = para

                heading_record = {
                    "text": para,
                    "page": page_num,
                    "word_count": estimate_word_count(para),
                }
                chunk_paragraphs.append(heading_record)
                current_word_count += heading_record["word_count"]
                continue

            para_record = {
                "text": para,
                "page": page_num,
                "word_count": estimate_word_count(para),
            }

            # If adding this paragraph would exceed target, flush first.
            if chunk_paragraphs and (current_word_count + para_record["word_count"] > target_words):
                chunk_counter = flush_chunk(
                    chunks=chunks,
                    chunk_paragraphs=chunk_paragraphs,
                    current_section=current_section,
                    chunk_counter=chunk_counter,
                )

                overlap_paragraphs, _ = build_overlap_text(chunk_paragraphs, overlap_words)
                chunk_paragraphs = overlap_paragraphs.copy()
                current_word_count = sum(p["word_count"] for p in chunk_paragraphs)

            chunk_paragraphs.append(para_record)
            current_word_count += para_record["word_count"]

    # Flush final chunk
    chunk_counter = flush_chunk(
        chunks=chunks,
        chunk_paragraphs=chunk_paragraphs,
        current_section=current_section,
        chunk_counter=chunk_counter,
    )

    return chunks


def load_extracted_pages(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def is_heading_only_chunk(chunk_paragraphs: list[dict[str, Any]]) -> bool:
    """
    True when the chunk contains only a single heading paragraph and no body text.
    """
    if len(chunk_paragraphs) != 1:
        return False
    return is_heading(chunk_paragraphs[0]["text"])