from fastapi import APIRouter, UploadFile, File, Depends, Header, HTTPException
import uuid
from typing import Optional
from datetime import datetime

router = APIRouter()

# Mock database
documents_db = []

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    # For mocking, just return a dummy username from the header (in real this will decode jwt)
    return "testuser"

@router.post("", status_code=202)
async def upload_document(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    doc_id = str(uuid.uuid4())
    
    # Store mocked document info
    new_doc = {
        "document_id": doc_id,
        "filename": file.filename,
        "upload_date": datetime.utcnow().isoformat() + "Z",
        "status": "processing",
        "page_count": None,
        "user": user
    }
    documents_db.append(new_doc)
    
    return {
        "message": "PDF uploaded, processing started",
        "document_id": doc_id,
        "status": "processing"
    }

@router.get("")
async def list_documents(user: str = Depends(get_current_user)):
    user_docs = [doc for doc in documents_db if doc["user"] == user]
    # Filter out user key before returning
    return [{k: v for k, v in doc.items() if k != "user"} for doc in user_docs]

@router.delete("/{document_id}")
async def delete_document(document_id: str, user: str = Depends(get_current_user)):
    global documents_db
    doc_to_delete = next((d for d in documents_db if d["document_id"] == document_id and d["user"] == user), None)
    
    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Document not found or not owned by user")
        
    documents_db = [d for d in documents_db if d["document_id"] != document_id]
    
    return {
        "message": "Document and all associated data deleted",
        "document_id": document_id
    }
