"""
Cliente Qdrant para api-core.

Guarda mensajes de conversación como chunks en la colección conversation_chunks.
Adapta el patrón de vector-store/client.py para uso interno en api-core.

Degradación gratuita: si el embedding falla o Qdrant no está disponible,
se registra una advertencia y la operación se omite sin lanzar excepción.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION = "conversation_chunks"


class ConversationChunkClient:
    """Inserta chunks de conversación en Qdrant usando embeddings del llm-runtime."""

    def __init__(self) -> None:
        self._qdrant: QdrantClient | None = None

    def initialize(self) -> None:
        """Conecta al servidor Qdrant. Llamar desde lifespan de FastAPI."""
        self._qdrant = QdrantClient(url=settings.qdrant_url)

    async def _embed(self, text: str) -> list[float] | None:
        """
        Llama a llm-runtime /v1/embeddings y devuelve el vector.
        Devuelve None si el servicio no está disponible.
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.llm_base_url}/embeddings",
                    json={"model": settings.embedding_model, "input": text},
                )
                resp.raise_for_status()
                data = resp.json()
                return data["data"][0]["embedding"]
        except Exception as exc:
            logger.warning("Embedding fallido, se omite Qdrant: %s", exc)
            return None

    async def save_message(
        self,
        text: str,
        role: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """
        Genera embedding y guarda el chunk en Qdrant.
        Fallo silencioso: nunca propaga excepciones al caller.
        """
        if self._qdrant is None:
            return

        vector = await self._embed(text)
        if vector is None:
            return

        point_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "text":       text,
            "role":       role,
            "source":     "conversation",
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "tags":       tags or [],
            "session_id": session_id,
        }

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._qdrant.upsert(  # type: ignore[union-attr]
                    collection_name=COLLECTION,
                    points=[PointStruct(id=point_id, vector=vector, payload=payload)],
                ),
            )
        except Exception as exc:
            logger.warning("Error guardando chunk en Qdrant: %s", exc)


# Singleton compartido por toda la app
qdrant_chunks = ConversationChunkClient()
