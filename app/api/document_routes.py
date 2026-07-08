from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.chunking_service import chunk_text
from app.services.document_extraction_service import (
    SUPPORTED_EXTENSIONS,
    extract_text_from_upload,
    get_file_extension,
)
from app.services.embedding_service import generate_embedding, serialize_embedding
from app.services.search_cache import clear_search_cache
from app.services.vector_store import upsert_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    document: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new document and save it in PostgreSQL.
    """
    embedding = generate_embedding(document.content)
    new_document = Document(
        title=document.title,
        content=document.content,
        embedding=serialize_embedding(embedding),
        user_id=current_user.id,
    )

    # Add the new object to the current database session.
    db.add(new_document)

    # Commit saves the change permanently in the database.
    db.commit()

    # Refresh loads generated values, such as id and created_at.
    db.refresh(new_document)

    upsert_document(
        document_id=new_document.id,
        embedding=embedding,
        metadata={
            "user_id": current_user.id,
            "title": new_document.title,
            "content": new_document.content,
            "source_filename": new_document.source_filename,
            "chunk_index": new_document.chunk_index,
            "created_at": new_document.created_at.isoformat(),
        },
    )
    clear_search_cache()

    return new_document


@router.post("/upload", response_model=list[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a supported file, split it into chunks, and store each chunk.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename.")

    if get_file_extension(file.filename) not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Please upload one of: {supported}.",
        )

    file_bytes = await file.read()

    try:
        file_text = extract_text_from_upload(file.filename, file_bytes)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Text file must be valid UTF-8.") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text: {exc}") from exc

    chunks = chunk_text(file_text)

    if not chunks:
        raise HTTPException(status_code=400, detail="File is empty.")

    saved_documents = []
    chunk_embeddings = []

    for index, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk)
        chunk_embeddings.append(embedding)
        saved_documents.append(
            Document(
                title=file.filename,
                content=chunk,
                embedding=serialize_embedding(embedding),
                source_filename=file.filename,
                chunk_index=index,
                user_id=current_user.id,
            )
        )

    db.add_all(saved_documents)
    db.commit()

    for document, embedding in zip(saved_documents, chunk_embeddings):
        db.refresh(document)
        upsert_document(
            document_id=document.id,
            embedding=embedding,
            metadata={
                "user_id": current_user.id,
                "title": document.title,
                "content": document.content,
                "source_filename": document.source_filename,
                "chunk_index": document.chunk_index,
                "created_at": document.created_at.isoformat(),
            },
        )

    clear_search_cache()
    return saved_documents


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all documents from PostgreSQL.
    """
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
