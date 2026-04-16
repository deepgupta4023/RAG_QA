from __future__ import annotations

import re
from typing import Any

from app.config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL_NAME
from app.services.chroma_service import ChromaService


_TOKEN_RE = re.compile(r"\b[a-zA-Z0-9]+\b")

# Small stopword list so overlap focuses on meaningful terms
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "had", "has", "have", "in", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "this", "to", "was", "were", "what", "which",
    "who", "with", "would",
}


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _keyword_set(text: str) -> set[str]:
    return {t for t in _tokenize(text) if t not in _STOPWORDS and len(t) > 1}


def _phrase_hits(question: str, text: str) -> int:
    """
    Reward chunks that contain multi-word phrases from the query.
    Only checks 2-gram and 3-gram phrases from the question.
    """
    q_tokens = [t for t in _tokenize(question) if t not in _STOPWORDS]
    lowered_text = text.lower()

    hits = 0

    # bigrams
    for i in range(len(q_tokens) - 1):
        phrase = f"{q_tokens[i]} {q_tokens[i+1]}"
        if phrase in lowered_text:
            hits += 1

    # trigrams
    for i in range(len(q_tokens) - 2):
        phrase = f"{q_tokens[i]} {q_tokens[i+1]} {q_tokens[i+2]}"
        if phrase in lowered_text:
            hits += 2

    return hits


def _lexical_score(question: str, text: str, section: str | None = None) -> float:
    """
    Score based on keyword overlap + phrase hits + mild section bonus.
    """
    q_keywords = _keyword_set(question)
    t_keywords = _keyword_set(text)

    if not q_keywords:
        return 0.0

    overlap = q_keywords.intersection(t_keywords)
    overlap_score = float(len(overlap))

    phrase_score = float(_phrase_hits(question, text))

    section_bonus = 0.0
    if section:
        section_text = section.lower()
        # reward if question keywords appear in section title
        for kw in q_keywords:
            if kw in section_text:
                section_bonus += 0.5

    return overlap_score + phrase_score + section_bonus


class Retriever:
    def __init__(self) -> None:
        self.chroma_service = ChromaService(
            persist_dir=str(CHROMA_DIR),
            collection_name=COLLECTION_NAME,
            embed_model_name=EMBED_MODEL_NAME,
        )

    def retrieve(
        self,
        question: str,
        k: int = 5,
        initial_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Two-stage retrieval:
        1. Dense retrieve from Chroma
        2. Lexically rerank the top initial_k results
        """
        raw = self.chroma_service.query(question=question, n_results=initial_k)

        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        results: list[dict[str, Any]] = []
        for idx in range(len(ids)):
            metadata = metadatas[idx] or {}
            document = documents[idx] or ""
            distance = float(distances[idx]) if idx < len(distances) else None

            lexical = _lexical_score(
                question=question,
                text=document,
                section=metadata.get("section"),
            )

            # Lower cosine distance is better, so use negative distance as dense score
            dense_score = -distance if distance is not None else 0.0

            # Weighted combined score:
            # lexical signal gets a stronger influence because that is what is failing now
            combined_score = (0.65 * lexical) + (0.35 * dense_score)

            results.append(
                {
                    "chunk_id": metadata.get("chunk_id", ids[idx]),
                    "page_start": metadata.get("page_start"),
                    "page_end": metadata.get("page_end"),
                    "section": metadata.get("section"),
                    "text": document,
                    "distance": distance,
                    "word_count": metadata.get("word_count"),
                    "lexical_score": lexical,
                    "dense_score": dense_score,
                    "combined_score": combined_score,
                }
            )

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:k]