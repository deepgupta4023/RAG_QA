import json
import sys
from pathlib import Path

# Ensure project root is importable when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.answer_service import AnswerService  # noqa: E402
from app.services.retriever import Retriever  # noqa: E402

QUESTIONS_PATH = PROJECT_ROOT / "eval" / "questions.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "eval_results.json"


def load_questions(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Questions file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def truncate(text: str, limit: int = 300) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def evaluate_question(
    question_item: dict,
    retriever: Retriever,
    answer_service: AnswerService,
    k: int = 5,
    initial_k: int = 10,
) -> dict:
    question = question_item["question"]
    expected_note = question_item.get("expected_note", "")

    retrieved_chunks = retriever.retrieve(
        question=question,
        k=k,
        initial_k=initial_k,
    )

    result = answer_service.answer(
        question=question,
        retrieved_chunks=retrieved_chunks,
    )

    return {
        "id": question_item.get("id"),
        "question": question,
        "expected_note": expected_note,
        "answer": result["answer"],
        "sources": result["sources"],
        "retrieved_preview": [
            {
                "chunk_id": chunk.get("chunk_id"),
                "section": chunk.get("section"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "distance": chunk.get("distance"),
                "lexical_score": chunk.get("lexical_score"),
                "combined_score": chunk.get("combined_score"),
                "preview": truncate(chunk.get("text", "")),
            }
            for chunk in retrieved_chunks
        ],
        "manual_status": "",
        "failure_reason": "",
    }


def main() -> None:
    questions = load_questions(QUESTIONS_PATH)

    retriever = Retriever()
    answer_service = AnswerService()

    results = []
    for idx, question_item in enumerate(questions, start=1):
        print(f"[{idx}/{len(questions)}] Evaluating: {question_item['question']}")
        eval_result = evaluate_question(
            question_item=question_item,
            retriever=retriever,
            answer_service=answer_service,
            k=5,
            initial_k=10,
        )
        results.append(eval_result)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved eval results to: {OUTPUT_PATH}")
    print("Review the file and fill in 'manual_status' and 'failure_reason' honestly.")


if __name__ == "__main__":
    main()