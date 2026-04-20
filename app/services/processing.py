import re
from io import BytesIO

from pypdf import PdfReader

from app.database import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.object_storage import download_object_bytes


def split_text_into_chunks(text: str) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    if paragraphs:
        return paragraphs

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines


def process_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        pdf_bytes = download_object_bytes(document.storage_path)
        reader = PdfReader(BytesIO(pdf_bytes))
        extracted_pages = [page.extract_text() or "" for page in reader.pages]
        raw_text = "\n\n".join(page.strip() for page in extracted_pages if page.strip())
        chunks = split_text_into_chunks(raw_text)

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete()

        for index, chunk_text in enumerate(chunks):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    text=chunk_text,
                )
            )

        document.page_count = len(reader.pages)
        document.status = "ready" if chunks else "failed"
        db.commit()
    except Exception:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
