from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from app.services.prompt_builder import build_answer_prompt
from dotenv import load_dotenv

load_dotenv()


class AnswerService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=api_key)

    def answer(
        self,
        question: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a grounded answer from retrieved chunks.
        Returns:
            {
                "answer": "...",
                "sources": [...]
            }
        """
        prompt = build_answer_prompt(question, retrieved_chunks)

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        answer_text = response.output_text.strip()

        sources = [
            {
                "chunk_id": chunk.get("chunk_id"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "section": chunk.get("section"),
            }
            for chunk in retrieved_chunks
        ]

        return {
            "answer": answer_text,
            "sources": sources,
        }