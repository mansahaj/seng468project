import re
from io import BytesIO

from pypdf import PdfReader

from app.database import SessionLocal
from app.embeddings import embed_texts
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.object_storage import download_object_bytes
from app.vector_store import delete_document_vectors, upsert_chunk_vectors


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

        delete_document_vectors(document.id)
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete()

        chunk_rows = []
        for index, chunk_text in enumerate(chunks):
            chunk_row = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                text=chunk_text,
            )
            db.add(chunk_row)
            chunk_rows.append(chunk_row)

        db.flush()

        vectors = embed_texts([chunk.text for chunk in chunk_rows])
        upsert_chunk_vectors(
            [
                {
                    "chunk_id": chunk.id,
                    "document_id": document.id,
                    "filename": document.filename,
                    "user_id": document.user_id,
                    "text": chunk.text,
                    "vector": vector,
                }
                for chunk, vector in zip(chunk_rows, vectors)
            ]
        )

        document.page_count = len(reader.pages)
        document.status = "ready" if chunks else "failed"
        db.commit()
    except Exception:
        db.rollback()
        delete_document_vectors(document_id)
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
