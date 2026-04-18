import argparse
import statistics
import sys
import time
from pathlib import Path
import json


# Ensure project root is importable when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_JSON = PROJECT_ROOT / "data" / "processed" / "retrieval_benchmark_timing.json"

from app.services.retriever import Retriever 

try:
    from app.services.answer_service import AnswerService 
    HAS_ANSWER_SERVICE = True
except Exception:
    HAS_ANSWER_SERVICE = False


DEFAULT_QUESTIONS = [
    "Is Microsoft profitable?",
    "What was Microsoft's revenue in fiscal year 2025?",
    "What is Microsoft Elevate?",
]


def timed_retrieval(retriever: Retriever, question: str, k: int, initial_k: int):
    start = time.perf_counter()
    results = retriever.retrieve(question=question, k=k, initial_k=initial_k)
    end = time.perf_counter()
    return results, end - start


def timed_answer(answer_service, question: str, retrieved_chunks):
    start = time.perf_counter()
    result = answer_service.answer(question=question, retrieved_chunks=retrieved_chunks)
    end = time.perf_counter()
    return result, end - start


def summarize(label: str, values: list[float]) -> None:
    if not values:
        print(f"{label}: no data")
        return None

    values_ms = [v * 1000 for v in values]
    p50 = statistics.median(values_ms)
    p95 = values_ms[0] if len(values_ms) == 1 else sorted(values_ms)[max(0, int(len(values_ms) * 0.95) - 1)]

    print(f"{label}")
    print(f"  runs : {len(values_ms)}")
    print(f"  min  : {min(values_ms):.2f} ms")
    print(f"  max  : {max(values_ms):.2f} ms")
    print(f"  mean : {statistics.mean(values_ms):.2f} ms")
    print(f"  p50  : {p50:.2f} ms")
    print(f"  p95  : {p95:.2f} ms")

    return{
            "runs" : f"{len(values_ms)}",
            "min"  : f"{min(values_ms):.2f} ms",
            "max"  : f"{max(values_ms):.2f} ms",
            "mean" : f"{statistics.mean(values_ms):.2f} ms",
            "p50"  : f"{p50:.2f} ms",
            "p95"  : f"{p95:.2f} ms"
                
            }

def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark cold and warm retrieval.")
    parser.add_argument("--question", type=str, default=None, help="Single question to benchmark")
    parser.add_argument("--k", type=int, default=5, help="Final number of results returned")
    parser.add_argument("--initial-k", type=int, default=10, help="Initial candidates before reranking")
    parser.add_argument("--warm-runs", type=int, default=10, help="Number of warm retrieval runs")
    parser.add_argument(
        "--include-answer",
        action="store_true",
        help="Also benchmark full answer generation (requires OPENAI_API_KEY and answer_service.py)",
    )
    args = parser.parse_args()

    questions = [args.question] if args.question else DEFAULT_QUESTIONS

    print("=" * 80)
    print("Benchmarking retrieval")
    print("=" * 80)
    print(f"Questions     : {len(questions)}")
    print(f"k             : {args.k}")
    print(f"initial_k     : {args.initial_k}")
    print(f"warm_runs     : {args.warm_runs}")
    print(f"include_answer: {args.include_answer}")
    print("=" * 80)

    # Cold retrieval
    retriever = Retriever()
    cold_retrieval_times = []
    warm_retrieval_times = []

    cold_answer_times = []
    warm_answer_times = []

    answer_service = None
    if args.include_answer:
        if not HAS_ANSWER_SERVICE:
            raise RuntimeError("answer_service.py could not be imported.")
        answer_service = AnswerService()

    for q_idx, question in enumerate(questions, start=1):
        print(f"\nQuestion {q_idx}: {question}")

        # Cold retrieval = first retrieval for this retriever instance
        retrieved_chunks, cold_t = timed_retrieval(
            retriever=retriever,
            question=question,
            k=args.k,
            initial_k=args.initial_k,
        )
        cold_retrieval_times.append(cold_t)
        print(f"  Cold retrieval : {cold_t * 1000:.2f} ms")

        if args.include_answer and answer_service is not None:
            _, cold_answer_t = timed_answer(
                answer_service=answer_service,
                question=question,
                retrieved_chunks=retrieved_chunks,
            )
            cold_answer_times.append(cold_answer_t)
            print(f"  Cold full answer: {cold_answer_t * 1000:.2f} ms")

        # Warm retrieval = repeat on same retriever instance
        for run_idx in range(args.warm_runs):
            retrieved_chunks, warm_t = timed_retrieval(
                retriever=retriever,
                question=question,
                k=args.k,
                initial_k=args.initial_k,
            )
            warm_retrieval_times.append(warm_t)

            if args.include_answer and answer_service is not None:
                _, warm_answer_t = timed_answer(
                    answer_service=answer_service,
                    question=question,
                    retrieved_chunks=retrieved_chunks,
                )
                warm_answer_times.append(warm_answer_t)

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    output_dict={}
    output_dict["Cold retrieval"]= summarize("Cold retrieval", cold_retrieval_times)
    print()
    output_dict["Warm retrieval"]=summarize("Warm retrieval", warm_retrieval_times)

    if args.include_answer:
        print()
        output_dict["Cold full answer"]= summarize("Cold full answer", cold_answer_times)
        print()
        output_dict["Warm full answer"]=summarize("Warm full answer", warm_answer_times)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output_dict, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()