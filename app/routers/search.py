from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth_utils import get_current_user
from app.database import get_db
from app.embeddings import embed_text
from app.models.user import User
from app.vector_store import search_chunk_vectors

router = APIRouter()


@router.get("")
async def search_documents(
    q: str = Query(..., description="The query to search for"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.username == user).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        query_vector = embed_text(q)
        return search_chunk_vectors(query_vector, db_user.id, limit=5)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Semantic search is temporarily unavailable",
        ) from exc
