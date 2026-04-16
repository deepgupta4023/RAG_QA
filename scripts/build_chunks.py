from __future__ import annotations

import json
from pathlib import Path

from scripts.chunking import build_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "extracted_pages.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing extracted pages file: {INPUT_PATH}. Run the PDF extraction step first."
        )

    pages = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    chunks = build_chunks(pages=pages, target_words=350, overlap_words=60)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Built {len(chunks)} chunks")
    print(f"Saved to: {OUTPUT_PATH}")

    if chunks:
        print("\nFirst chunk preview:\n")
        print(json.dumps(chunks[0], ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
