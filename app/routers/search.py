from fastapi import APIRouter, Header, HTTPException, Query, Depends
from typing import Optional

router = APIRouter()

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    # In a real app we decode the JWT token here
    return "testuser"

@router.get("")
async def search_documents(q: str = Query(..., description="The query to search for"), user: str = Depends(get_current_user)):
    # Mock search logic
    return [
        {
            "text": f"Machine learning optimization techniques include gradient descent, Adam optimizer, and stochastic methods that improve convergence rates significantly. Query was: {q}",
            "score": 0.942,
            "document_id": "uuid-123",
            "filename": "research_paper.pdf"
        },
        {
            "text": "Optimization in neural networks requires careful tuning of hyperparameters such as learning rate and batch size.",
            "score": 0.867,
            "document_id": "uuid-456",
            "filename": "textbook_chapter.pdf"
        },
        {
            "text": "Another relevant paragraph about optimization...",
            "score": 0.812,
            "document_id": "uuid-123",
            "filename": "research_paper.pdf"
        },
        {
            "text": "Fourth relevant paragraph...",
            "score": 0.755,
            "document_id": "uuid-789",
            "filename": "ml_handbook.pdf"
        },
        {
            "text": "Fifth relevant paragraph...",
            "score": 0.701,
            "document_id": "uuid-456",
            "filename": "textbook_chapter.pdf"
        }
    ]
