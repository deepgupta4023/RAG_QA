import json
import sys
from pathlib import Path

# Ensure project root is importable when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (  # noqa: E402
    CHROMA_DIR,
    CHUNKS_PATH,
    COLLECTION_NAME,
    DOCUMENT_ID,
    EMBED_MODEL_NAME,
    UPSERT_BATCH_SIZE,
)
from app.services.chroma_service import ChromaService  # noqa: E402


def load_chunks_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")

    chunks: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

            record["document_id"] = DOCUMENT_ID
            chunks.append(record)

    return chunks


def batched(items: list[dict], batch_size: int) -> list[list[dict]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def main() -> None:
    print(f"Loading chunks from: {CHUNKS_PATH}")
    chunks = load_chunks_jsonl(CHUNKS_PATH)
    print(f"Loaded {len(chunks)} chunks")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    print("Initializing Chroma service...")
    chroma_service = ChromaService(
        persist_dir=str(CHROMA_DIR),
        collection_name=COLLECTION_NAME,
        embed_model_name=EMBED_MODEL_NAME,
    )
    chroma_service.reset_collection()
    print("Deleting old Data...")

    print(f"Using collection: {COLLECTION_NAME}")

    batches = batched(chunks, UPSERT_BATCH_SIZE)
    for idx, batch in enumerate(batches, start=1):
        chroma_service.upsert_chunks(batch)
        print(f"Upserted batch {idx}/{len(batches)} ({len(batch)} chunks)")

    print(f"Final collection count: {chroma_service.count()}")
    print("Ingestion completed successfully.")


if __name__ == "__main__":
    main()