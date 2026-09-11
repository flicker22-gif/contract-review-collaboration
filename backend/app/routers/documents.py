import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Annotation, Document, Paragraph
from ..parsers import parse_document
from ..schemas import DocumentDetail, DocumentListItem, DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    ".docx": "docx",
    ".pdf": "pdf",
}


@router.post("/", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile, db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 .docx 或 .pdf 文件")

    file_type = ALLOWED_TYPES[suffix]
    storage_name = f"{uuid.uuid4().hex}{suffix}"
    storage_path = STORAGE_DIR / storage_name

    with storage_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        paragraphs = parse_document(storage_path, file_type)
    except Exception as exc:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"文件解析失败: {exc}")

    if not paragraphs:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="未能从文件中提取到文本内容")

    document = Document(
        filename=file.filename or storage_name,
        file_type=file_type,
        storage_path=str(storage_path),
    )
    db.add(document)
    db.flush()  # 拿到 document.id

    for idx, text in enumerate(paragraphs):
        db.add(Paragraph(document_id=document.id, idx=idx, text=text))

    db.commit()
    db.refresh(document)
    return document


@router.get("/", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    counts = (
        db.query(
            Annotation.document_id,
            func.count(Annotation.id),
            func.sum(Annotation.status == "open"),
        )
        .group_by(Annotation.document_id)
        .all()
    )
    count_map = {doc_id: (total, open_count or 0) for doc_id, total, open_count in counts}
    return [
        DocumentListItem(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            created_at=doc.created_at,
            annotation_count=count_map.get(doc.id, (0, 0))[0],
            open_count=count_map.get(doc.id, (0, 0))[1],
        )
        for doc in docs
    ]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    Path(document.storage_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
