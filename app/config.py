from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHROMA_DIR = DATA_DIR / "chroma_db"

CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"

COLLECTION_NAME = "msft_annual_report_2025"
DOCUMENT_ID = "msft_ar_2025"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

UPSERT_BATCH_SIZE = 64