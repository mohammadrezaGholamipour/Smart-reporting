import time

import httpx

from app.core.config import settings

BATCH_SIZE = 32
MAX_ATTEMPTS = 3


def _post_with_retry(client: httpx.Client, headers: dict, payload: dict) -> dict:
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.post(
                settings.embedding_base_url, headers=headers, json=payload
            )
            # خطای ۵xx و ۴۲۹ موقتی‌اند؛ بقیهٔ خطاها بلافاصله گزارش می‌شوند.
            if response.status_code >= 500 or response.status_code == 429:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            return response.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_error = exc
            retryable = isinstance(exc, httpx.TransportError) or (
                exc.response.status_code >= 500 or exc.response.status_code == 429
            )
            if not retryable or attempt == MAX_ATTEMPTS:
                break
            time.sleep(0.8 * attempt)

    raise RuntimeError(f"Embedding service unavailable: {last_error}") from last_error


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.embedding_model:
        raise ValueError("EMBEDDING_MODEL is not configured in .env")

    if not texts:
        return []

    headers = {"Content-Type": "application/json"}

    if settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.embedding_api_key}"

    embeddings: list[list[float]] = []

    with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]

            result = _post_with_retry(
                client,
                headers,
                {"model": settings.embedding_model, "input": batch},
            )
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
