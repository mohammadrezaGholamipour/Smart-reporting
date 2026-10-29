from app.services.embedding_client import embed_texts
from fastapi import APIRouter, Depends, HTTPException
from app.services.vector_store import search_chunks
from app.schemas.search import SearchRequest
from sqlalchemy.orm import Session
from app.models import DataSource
from app.store.db import get_db



router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@router.post("")
def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Query cannot be empty.",
        )

    if request.source_id is not None:
        source = db.get(DataSource, request.source_id)

        if source is None:
            raise HTTPException(
                status_code=404,
                detail="Source not found.",
            )

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
        raise HTTPException(
            status_code=502,
            detail=f"Semantic search failed: {exc}",
        ) from exc
