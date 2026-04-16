from __future__ import annotations

from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer


class ChromaService:
    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embed_model_name: str,
    ) -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embed_model_name = embed_model_name

        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.embedding_model = SentenceTransformer(self.embed_model_name)
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> Collection:
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def upsert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return

        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = []

        for chunk in chunks:
            metadata = {
                "chunk_id": chunk["chunk_id"],
                "page_start": int(chunk["page_start"]),
                "page_end": int(chunk["page_end"]),
                "section": chunk["section"],
                "word_count": int(chunk["word_count"]),
                "document_id": chunk["document_id"],
            }
            metadatas.append(metadata)

        embeddings = self.embed_texts(documents)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def count(self) -> int:
        return self.collection.count()

    def query(self, question: str, n_results: int = 5) -> dict[str, Any]:
        query_embedding = self.embed_texts([question])[0]
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )