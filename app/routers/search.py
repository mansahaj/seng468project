import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth_utils import get_current_user
from app.database import get_db
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.user import User

router = APIRouter()


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def calculate_score(query: str, text: str) -> float:
    query_terms = tokenize(query)
    text_terms = tokenize(text)
    if not query_terms or not text_terms:
        return 0.0

    overlap = len(query_terms & text_terms)
    return round(min(overlap / len(query_terms), 1.0), 3)


@router.get("")
async def search_documents(
    q: str = Query(..., description="The query to search for"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.username == user).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.user_id == db_user.id, Document.status == "ready")
        .all()
    )

    scored_results = []
    for chunk, document in rows:
        score = calculate_score(q, chunk.text)
        if score <= 0:
            continue
        scored_results.append(
            {
                "text": chunk.text,
                "score": score,
                "document_id": document.id,
                "filename": document.filename,
            }
        )

    scored_results.sort(key=lambda item: item["score"], reverse=True)
    return scored_results[:5]
