import httpx

from app.core.config import settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.embedding_model:
        raise ValueError("EMBEDDING_MODEL is not configured in .env")

    if not texts:
        return []

    headers = {"Content-Type": "application/json"}

    if settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.embedding_api_key}"

    embeddings = []

    with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
        for start in range(0, len(texts), 32):
            batch = texts[start : start + 32]

            response = client.post(
                settings.embedding_base_url,
                headers=headers,
                json={
                    "model": settings.embedding_model,
                    "input": batch,
                },
            )
            response.raise_for_status()

            result = response.json()
            data = result.get("data")

            if not isinstance(data, list) or len(data) != len(batch):
                raise ValueError("Invalid embedding API response")

            data.sort(key=lambda item: item.get("index", 0))

            for item in data:
                vector = item.get("embedding")

                if not isinstance(vector, list) or not vector:
                    raise ValueError("Embedding vector is missing")

                embeddings.append(vector)

    return embeddings
