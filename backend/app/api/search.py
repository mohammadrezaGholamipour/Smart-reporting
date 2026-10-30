from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import DataSource
from app.schemas.search import SearchRequest
from app.services.embedding_client import embed_texts
from app.services.vector_store import search_chunks
from app.store.db import get_db

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("")
def semantic_search(request: SearchRequest, db: Session = Depends(get_db)):
    query = request.query.strip()

    if not query:
        raise HTTPException(422, "Query cannot be empty.")

    if request.source_id is not None and db.get(DataSource, request.source_id) is None:
        raise HTTPException(404, "Source not found.")

    try:
        query_embedding = embed_texts([query])[0]
        results = search_chunks(
            query_embedding=query_embedding,
            source_id=request.source_id,
            top_k=request.top_k,
        )
        return {
            "query": query,
            "source_id": request.source_id,
            "result_count": len(results),
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(502, f"Semantic search failed: {exc}") from exc
