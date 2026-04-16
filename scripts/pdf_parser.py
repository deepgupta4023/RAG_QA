from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


class PDFExtractionError(Exception):
    """Raised when PDF extraction fails."""


def extract_pages(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Extract raw text from a PDF one page at a time.

    Returns a list of dicts like:
    {
        "page": 1,
        "raw_text": "...",
        "char_count": 1234,
        "has_text": True,
    }

    Notes:
    - Uses sorted text extraction to improve reading order.
    - Page numbers are 1-based in the returned records.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    records: list[dict[str, Any]] = []

    try:
        with fitz.open(path) as doc:
            for index, page in enumerate(doc, start=1):
                raw_text = page.get_text("text", sort=True) or ""
                records.append(
                    {
                        "page": index,
                        "raw_text": raw_text,
                        "char_count": len(raw_text),
                        "has_text": bool(raw_text.strip()),
                    }
                )
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise PDFExtractionError(f"Failed to extract PDF: {path}") from exc

    return records
