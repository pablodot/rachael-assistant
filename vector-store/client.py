"""
Cliente Qdrant reutilizable para Rachael.

Política de chunking (SPEC.md §10):
  - Tamaño de chunk: 400-800 tokens
  - Solapamiento:    10-20%  (~60-120 tokens para un chunk de 600)
  - Metadatos:       source, timestamp, tags, session_id

Uso rápido:
    from vector_store.client import VectorStoreClient

    vs = VectorStoreClient()
    vs.upsert("conversation_chunks", points=[...])
    results = vs.search("conversation_chunks", query_vector=[...], limit=5)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    PointStruct,
    ScoredPoint,
)

# ── Constantes de chunking ────────────────────────────────────────────────────

# Tokens por chunk (ventana recomendada: 400-800)
CHUNK_SIZE_TOKENS: int = 600
# Solapamiento ~15% del tamaño de chunk
CHUNK_OVERLAP_TOKENS: int = 90

# ── Cliente ───────────────────────────────────────────────────────────────────

class VectorStoreClient:
    """
    Capa fina sobre QdrantClient con helpers para las colecciones de Rachael.

    Args:
        url:   URL del servidor Qdrant (default: QDRANT_URL env o localhost).
        api_key: API key si Qdrant corre con autenticación.
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self._client = QdrantClient(url=self.url, api_key=api_key)

    # ── Escritura ─────────────────────────────────────────────────────────────

    def upsert(
        self,
        collection: str,
        points: list[PointStruct],
    ) -> None:
        """Inserta o actualiza una lista de PointStruct en la colección."""
        self._client.upsert(collection_name=collection, points=points)

    def insert_chunk(
        self,
        collection: str,
        vector: list[float],
        text: str,
        source: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """
        Inserta un único chunk con los metadatos estándar de Rachael.

        Returns:
            El UUID asignado al punto.
        """
        point_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "text":       text,
            "source":     source,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "tags":       tags or [],
            "session_id": session_id,
        }
        if extra:
            payload.update(extra)

        self._client.upsert(
            collection_name=collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    def insert_chunks_from_text(
        self,
        collection: str,
        full_text: str,
        embed_fn: Any,          # callable(str) -> list[float]
        source: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
        chunk_size: int = CHUNK_SIZE_TOKENS,
        overlap: int = CHUNK_OVERLAP_TOKENS,
    ) -> list[str]:
        """
        Divide `full_text` en chunks con solapamiento y los inserta.

        La división es aproximada (por palabras), ya que tokenizar exactamente
        requeriría el tokenizador del modelo de embeddings.

        Args:
            embed_fn: función que recibe texto y devuelve un vector float.

        Returns:
            Lista de UUIDs insertados.
        """
        words = full_text.split()
        chunks: list[str] = []

        step = max(1, chunk_size - overlap)
        i = 0
        while i < len(words):
            chunk_words = words[i : i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += step

        ids: list[str] = []
        for chunk_text in chunks:
            vector = embed_fn(chunk_text)
            point_id = self.insert_chunk(
                collection=collection,
                vector=vector,
                text=chunk_text,
                source=source,
                session_id=session_id,
                tags=tags,
            )
            ids.append(point_id)

        return ids

    # ── Búsqueda ──────────────────────────────────────────────────────────────

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
    ) -> list[ScoredPoint]:
        """
        Búsqueda semántica por vector.

        Args:
            session_id: filtra por sesión si se especifica.
            tags:       filtra por al menos una etiqueta (primer tag de la lista).
            score_threshold: descarta resultados por debajo de este score.
        """
        query_filter: Filter | None = None

        conditions: list[FieldCondition] = []
        if session_id:
            conditions.append(
                FieldCondition(key="session_id", match=MatchValue(value=session_id))
            )
        if tags:
            # Filtra por el primer tag; para multi-tag añadir Should/Must conditions.
            conditions.append(
                FieldCondition(key="tags", match=MatchValue(value=tags[0]))
            )

        if conditions:
            query_filter = Filter(must=conditions)

        results = self._client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
        )
        return results

    def search_by_text(
        self,
        collection: str,
        query_text: str,
        embed_fn: Any,
        limit: int = 5,
        **kwargs: Any,
    ) -> list[ScoredPoint]:
        """Convierte `query_text` a vector y delega en `search`."""
        vector = embed_fn(query_text)
        return self.search(collection, vector, limit=limit, **kwargs)

    # ── Utilidades ────────────────────────────────────────────────────────────

    def delete_by_session(self, collection: str, session_id: str) -> None:
        """Elimina todos los puntos de una sesión concreta."""
        from qdrant_client.models import FilterSelector

        self._client.delete(
            collection_name=collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=session_id),
                        )
                    ]
                )
            ),
        )

    def collection_info(self, collection: str) -> dict[str, Any]:
        """Devuelve información básica de la colección."""
        info = self._client.get_collection(collection)
        return {
            "name":         collection,
            "vectors_count": info.vectors_count,
            "status":       str(info.status),
        }
