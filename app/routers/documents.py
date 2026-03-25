import os
from app.auth_utils import get_current_user
from fastapi import APIRouter, UploadFile, File, Depends, Header, HTTPException
import uuid
from typing import Optional
from datetime import datetime
from app.storage import documents_db, chunks_db

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

documents_db = []


@router.post("/", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    user: str = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    new_doc = {
        "document_id": doc_id,
        "filename": file.filename,
        "file_path": file_path,
        "upload_date": datetime.utcnow().isoformat() + "Z",
        "status": "processing",
        "page_count": None,
        "user": user
    }

    documents_db.append(new_doc)

    return {
        "message": "PDF uploaded and saved",
        "document_id": doc_id,
        "status": "processing"
    }


@router.get("/")
async def list_documents(user: str = Depends(get_current_user)):
    user_docs = [doc for doc in documents_db if doc["user"] == user]
    return [
        {k: v for k, v in doc.items() if k not in ["user", "file_path"]}
        for doc in user_docs
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: str = Depends(get_current_user)
):
    global documents_db

    doc_to_delete = next(
        (
            d for d in documents_db
            if d["document_id"] == document_id and d["user"] == user
        ),
        None
    )

    if not doc_to_delete:
        raise HTTPException(
            status_code=404,
            detail="Document not found or not owned by user"
        )

    if os.path.exists(doc_to_delete["file_path"]):
        os.remove(doc_to_delete["file_path"])

    documents_db = [
        d for d in documents_db if d["document_id"] != document_id
    ]

    return {
        "message": "Document and all associated data deleted",
        "document_id": document_id
    }