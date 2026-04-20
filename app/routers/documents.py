import os
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.auth_utils import get_current_user
from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.services.processing import process_document

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    db_user = db.query(User).filter(User.username == user).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    new_doc = Document(
        id=doc_id,
        user_id=db_user.id,
        filename=file.filename,
        storage_path=file_path,
        upload_date=datetime.utcnow(),
        status="processing",
        page_count=None,
    )
    db.add(new_doc)
    db.commit()
    background_tasks.add_task(process_document, doc_id)

    return {
        "message": "PDF uploaded, processing started",
        "document_id": doc_id,
        "status": "processing",
    }


@router.get("")
async def list_documents(
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.username == user).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    user_docs = (
        db.query(Document)
        .filter(Document.user_id == db_user.id)
        .order_by(Document.upload_date.desc())
        .all()
    )

    return [
        {
            "document_id": doc.id,
            "filename": doc.filename,
            "upload_date": doc.upload_date.isoformat() + "Z",
            "status": doc.status,
            "page_count": doc.page_count,
        }
        for doc in user_docs
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.username == user).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    doc_to_delete = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == db_user.id)
        .first()
    )

    if not doc_to_delete:
        raise HTTPException(
            status_code=404,
            detail="Document not found or not owned by user"
        )

    if os.path.exists(doc_to_delete.storage_path):
        os.remove(doc_to_delete.storage_path)

    db.delete(doc_to_delete)
    db.commit()

    return {
        "message": "Document and all associated data deleted",
        "document_id": document_id,
    }
