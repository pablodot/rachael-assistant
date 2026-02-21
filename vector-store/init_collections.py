"""
Inicializa las colecciones Qdrant para Rachael.

Colecciones (SPEC.md §10):
  - conversation_chunks  → fragmentos de conversaciones para RAG
  - notes                → notas del usuario
  - web_clips            → contenido extraído de páginas web

Política de chunking:
  - Tamaño: 400-800 tokens
  - Solapamiento: 10-20%
  - Metadatos: source, timestamp, tags, session_id

Ejecutar una sola vez al arrancar el stack, o cuando se necesite recrear.
"""

import os
import sys

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
)

# ── Configuración ────────────────────────────────────────────────────────────

QDRANT_URL  = os.getenv("QDRANT_URL", "http://localhost:6333")

# Dimensión del vector de embeddings.
# Ollama/nomic-embed-text → 768. Ajustar si se cambia el modelo.
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))

# Nombres de colecciones
COLLECTIONS = [
    "conversation_chunks",
    "notes",
    "web_clips",
]

# ── Lógica ───────────────────────────────────────────────────────────────────

def init_collections(client: QdrantClient, recreate: bool = False) -> None:
    """Crea (o recrea) las colecciones en Qdrant."""
    existing = {c.name for c in client.get_collections().collections}

    for name in COLLECTIONS:
        if name in existing:
            if recreate:
                print(f"[init] Borrando colección existente: {name}")
                client.delete_collection(name)
            else:
                print(f"[init] Colección ya existe, omitiendo: {name}")
                continue

        print(f"[init] Creando colección: {name}")
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
        print(f"[init] OK: {name}")

    print("[init] Colecciones listas.")


def main() -> None:
    recreate = "--recreate" in sys.argv

    print(f"[init] Conectando a Qdrant en {QDRANT_URL} ...")
    client = QdrantClient(url=QDRANT_URL)

    init_collections(client, recreate=recreate)


if __name__ == "__main__":
    main()
