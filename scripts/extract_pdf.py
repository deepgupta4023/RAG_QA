from __future__ import annotations

import json
from pathlib import Path

from scripts.pdf_parser import extract_pages
from scripts.text_cleaning import clean_page_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PDF = PROJECT_ROOT / "data" / "raw" / "2025_AnnualReport.pdf"
OUTPUT_JSON = PROJECT_ROOT / "data" / "processed" / "extracted_pages.json"


def main() -> None:
    if not INPUT_PDF.is_file():
        raise FileNotFoundError(
            f"Expected PDF at {INPUT_PDF}. Put the annual report there before running this script."
        )

    pages = extract_pages(INPUT_PDF)
    extracted_pages: list[dict] = []

    for page in pages:
        raw_text = page["raw_text"]
        cleaned_text = clean_page_text(raw_text)
        extracted_pages.append(
            {
                "page": page["page"],
                "raw_text": raw_text,
                "text": cleaned_text,
                "char_count": len(cleaned_text),
                "has_text": bool(cleaned_text),
            }
        )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(extracted_pages, f, ensure_ascii=False, indent=2)

    non_empty_pages = sum(1 for page in extracted_pages if page["has_text"])
    print(f"Extracted {len(extracted_pages)} pages")
    print(f"Pages with text: {non_empty_pages}")
    print(f"Saved output to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
