from fastapi import FastAPI, HTTPException

from app.schemas import AskRequest, AskResponse
from app.services.answer_service import AnswerService
from app.services.retriever import Retriever

app = FastAPI(title="PDF Q&A API", version="1.0.0")

retriever = Retriever()
answer_service = AnswerService()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    retrieved_chunks = retriever.retrieve(
        question=question,
        k=5,
        initial_k=10,
    )

    if not retrieved_chunks:
        return AskResponse(
            answer="I could not find relevant context in the document.",
            sources=[],
        )

    result = answer_service.answer(
        question=question,
        retrieved_chunks=retrieved_chunks,
    )

    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
    )