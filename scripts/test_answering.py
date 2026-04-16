import argparse
import sys
from pathlib import Path

# Ensure project root is importable when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.answer_service import AnswerService  # noqa: E402
from app.services.retriever import Retriever  # noqa: E402


def print_sources(sources: list[dict]) -> None:
    print("\nSources:")
    print("-" * 80)
    for idx, source in enumerate(sources, start=1):
        print(f"{idx}. Chunk ID : {source.get('chunk_id')}")
        print(f"   Pages    : {source.get('page_start')} -> {source.get('page_end')}")
        print(f"   Section  : {source.get('section')}")
        print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test retrieval + grounded answering")
    parser.add_argument(
        "question",
        nargs="?",
        default="Is Microsoft profitable?",
        help="Question to ask",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of retrieved chunks to pass to the answerer",
    )
    parser.add_argument(
        "--initial-k",
        type=int,
        default=10,
        help="Number of dense retrieval candidates before reranking",
    )
    args = parser.parse_args()

    retriever = Retriever()
    answer_service = AnswerService()

    retrieved_chunks = retriever.retrieve(
        question=args.question,
        k=args.k,
        initial_k=args.initial_k,
    )

    result = answer_service.answer(
        question=args.question,
        retrieved_chunks=retrieved_chunks,
    )

    print("=" * 80)
    print(f"Question: {args.question}")
    print("=" * 80)
    print("\nAnswer:\n")
    print(result["answer"])

    print_sources(result["sources"])


if __name__ == "__main__":
    main()