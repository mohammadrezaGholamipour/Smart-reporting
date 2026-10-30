from functools import lru_cache
from typing import Any, cast

from app.core.config import settings

COLLECTION_NAME = "pdf_chunks"


@lru_cache(maxsize=1)
def _get_client():
    # import تنبل: بدون نصب chromadb هم بقیهٔ برنامه بالا می‌آید.
    import chromadb

    return chromadb.PersistentClient(path=settings.chroma_dir)


def get_collection():
    # کلاینت فقط یک‌بار ساخته می‌شود (قبلاً در هر درخواست دوباره ساخته می‌شد).
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def store_chunks(
    source_id: int,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings count do not match")

    if not chunks:
        return 0

    collection = get_collection()

    ids = [
        f"source_{source_id}_page_{c['page_number']}_chunk_{c['chunk_index']}"
        for c in chunks
    ]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "source_id": source_id,
            "page_number": c["page_number"],
            "chunk_index": c["chunk_index"],
            "kind": c.get("kind", "text"),
        }
        for c in chunks
    ]

    # حذف قطعه‌های قبلی همین منبع تا دوباره‌کاری باعث باقی‌ماندن داده‌ی کهنه نشود.
    collection.delete(where=cast(Any, {"source_id": source_id}))

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=cast(Any, embeddings),
        metadatas=metadatas,
    )

    return len(ids)


def search_chunks(
    query_embedding: list[float],
    source_id: int | None = None,
    top_k: int = 3,
    max_distance: float | None = None,
) -> list[dict]:
    collection = get_collection()

    total = collection.count()
    if total == 0:
        return []

    if max_distance is None:
        max_distance = settings.retrieval_max_distance or None

    query_args: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, total),
        "include": ["documents", "metadatas", "distances"],
    }

    if source_id is not None:
        query_args["where"] = cast(Any, {"source_id": source_id})

    results = collection.query(**query_args)

    ids = results.get("ids")
    documents = results.get("documents")
    metadatas = results.get("metadatas")
    distances = results.get("distances")

    # وقتی فیلتر source_id چیزی پیدا نکند، لیست‌ها خالی‌اند؛ خطا نیست.
    if not ids or not ids[0] or not documents or not metadatas or not distances:
        return []

    items = []

    for index, chunk_id in enumerate(ids[0]):
        text = documents[0][index]
        metadata = metadatas[0][index]
        distance = distances[0][index]

        if text is None or metadata is None or distance is None:
            continue
        if max_distance is not None and distance > max_distance:
            continue

        items.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "metadata": metadata,
                "distance": distance,
            }
        )

    return items


def delete_source_chunks(source_id: int) -> None:
    get_collection().delete(where={"source_id": source_id})
