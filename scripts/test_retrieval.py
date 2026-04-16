import argparse
import sys
from pathlib import Path

# Ensure project root is importable when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.retriever import Retriever  # noqa: E402


def shorten(text: str, limit: int = 400) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def print_result(result: dict, rank: int) -> None:
    print(f"Rank          : {rank}")
    print(f"Chunk ID      : {result.get('chunk_id')}")
    print(f"Pages         : {result.get('page_start')} -> {result.get('page_end')}")
    print(f"Section       : {result.get('section')}")
    print(f"Distance      : {result.get('distance')}")
    print(f"Lexical Score : {result.get('lexical_score')}")
    print(f"Dense Score   : {result.get('dense_score')}")
    print(f"Combined Score: {result.get('combined_score')}")
    print(f"Words         : {result.get('word_count')}")
    print(f"Preview       : {shorten(result.get('text', ''))}")
    print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test retrieval against local Chroma DB")
    parser.add_argument(
        "question",
        nargs="?",
        default="What were Microsoft's three core business priorities?",
        help="Question to search for",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results to return after reranking",
    )
    parser.add_argument(
        "--initial-k",
        type=int,
        default=10,
        help="Number of dense results to fetch before reranking",
    )
    args = parser.parse_args()

    retriever = Retriever()
    results = retriever.retrieve(
        question=args.question,
        k=args.k,
        initial_k=args.initial_k,
    )

    print("=" * 80)
    print(f"Question: {args.question}")
    print(f"Top-k   : {args.k}")
    print("=" * 80)

    for idx, result in enumerate(results, start=1):
        print_result(result, idx)


if __name__ == "__main__":
    main()