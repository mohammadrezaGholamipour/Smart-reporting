from typing import Any, cast

import chromadb

from app.core.config import settings

COLLECTION_NAME = "pdf_chunks"


def get_collection():
    client = chromadb.PersistentClient(path=settings.chroma_dir)

    return client.get_or_create_collection(
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
        (
            f"source_{source_id}"
            f"_page_{chunk['page_number']}"
            f"_chunk_{chunk['chunk_index']}"
        )
        for chunk in chunks
    ]

    documents = [chunk["text"] for chunk in chunks]

    metadatas = [
        {
            "source_id": source_id,
            "page_number": chunk["page_number"],
            "chunk_index": chunk["chunk_index"],
        }
        for chunk in chunks
    ]

    # حذف قطعه‌های قبلی همین منبع
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
) -> list[dict]:
    collection = get_collection()

    # اگر منبع مشخص شده باشد، جست‌وجو محدود می‌شود.
    filters = {"source_id": source_id} if source_id is not None else None

    # count() تعداد کل رکوردها را برمی‌گرداند و
    # پارامتر where ندارد.
    total = collection.count()

    if total == 0:
        return []

    query_args: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, total),
        "include": [
            "documents",
            "metadatas",
            "distances",
        ],
    }

    if filters is not None:
        query_args["where"] = cast(Any, filters)

    results = collection.query(**query_args)

    ids = results["ids"]
    documents = results["documents"]
    metadatas = results["metadatas"]
    distances = results["distances"]

    if not ids or not ids[0]:
        return []

    # این فیلدها ممکن است در پاسخ خالی یا ناقص None باشند.
    if documents is None or metadatas is None or distances is None:
        raise ValueError("ChromaDB did not return the requested result fields")

    if not documents[0] or not metadatas[0] or not distances[0]:
        raise ValueError("ChromaDB returned incomplete search results")

    items = []

    for index, chunk_id in enumerate(ids[0]):
        text = documents[0][index]
        metadata = metadatas[0][index]
        distance = distances[0][index]

        if text is None or metadata is None or distance is None:
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
    collection = get_collection()

    collection.delete(
        where={"source_id": source_id}
    )