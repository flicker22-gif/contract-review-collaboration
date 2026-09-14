import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..diffing import diff_paragraphs
from ..models import Annotation, Document, Paragraph
from ..parsers import parse_document
from ..schemas import (
    DiffResponse,
    DiffStats,
    DiffVersionInfo,
    DocumentDetail,
    DocumentListItem,
    DocumentOut,
    VersionOut,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    ".docx": "docx",
    ".pdf": "pdf",
}


@router.post("/", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    base_document_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 .docx 或 .pdf 文件")

    # 基于已有版本上传：继承版本组，版本号 +1；否则自成一组
    base: Document | None = None
    if base_document_id is not None:
        base = db.get(Document, base_document_id)
        if not base:
            raise HTTPException(status_code=404, detail="基准版本不存在")

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

    if base is not None:
        latest = (
            db.query(func.max(Document.version_number))
            .filter(Document.group_id == base.group_id)
            .scalar()
        )
        group_id = base.group_id
        version_number = (latest or 1) + 1
    else:
        group_id = uuid.uuid4().hex
        version_number = 1

    document = Document(
        filename=file.filename or storage_name,
        file_type=file_type,
        storage_path=str(storage_path),
        group_id=group_id,
        version_number=version_number,
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
            group_id=doc.group_id,
            version_number=doc.version_number,
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


@router.get("/{document_id}/versions", response_model=list[VersionOut])
def list_versions(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    versions = (
        db.query(Document)
        .filter(Document.group_id == document.group_id)
        .order_by(Document.version_number)
        .all()
    )
    counts = (
        db.query(
            Annotation.document_id,
            func.count(Annotation.id),
            func.sum(Annotation.status == "open"),
        )
        .filter(
            Annotation.document_id.in_([v.id for v in versions])
            if versions
            else False
        )
        .group_by(Annotation.document_id)
        .all()
    )
    count_map = {doc_id: (total, open_count or 0) for doc_id, total, open_count in counts}
    return [
        VersionOut(
            id=v.id,
            version_number=v.version_number,
            filename=v.filename,
            file_type=v.file_type,
            created_at=v.created_at,
            annotation_count=count_map.get(v.id, (0, 0))[0],
            open_count=count_map.get(v.id, (0, 0))[1],
        )
        for v in versions
    ]


@router.get("/{document_id}/diff", response_model=DiffResponse)
def diff_document(
    document_id: int,
    against: int | None = None,
    db: Session = Depends(get_db),
):
    """对比当前版本（new）与指定版本 against（old）。

    不传 against 时默认取同组内的上一版本；当前版本已是第一版则 400。
    """
    new_doc = db.get(Document, document_id)
    if not new_doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if against is None:
        old_doc = (
            db.query(Document)
            .filter(
                Document.group_id == new_doc.group_id,
                Document.version_number < new_doc.version_number,
            )
            .order_by(Document.version_number.desc())
            .first()
        )
        if old_doc is None:
            raise HTTPException(status_code=400, detail="该合同只有一个版本，无法对比")
    else:
        old_doc = db.get(Document, against)
        if not old_doc or old_doc.group_id != new_doc.group_id:
            raise HTTPException(status_code=400, detail="只能对比同一合同的两个版本")
        if old_doc.id == new_doc.id:
            raise HTTPException(status_code=400, detail="请选择两个不同的版本")

    old_paragraphs = [
        p.text
        for p in sorted(old_doc.paragraphs, key=lambda p: p.idx)
    ]
    new_paragraphs = [
        p.text
        for p in sorted(new_doc.paragraphs, key=lambda p: p.idx)
    ]
    result = diff_paragraphs(old_paragraphs, new_paragraphs)

    return DiffResponse(
        old=DiffVersionInfo(
            id=old_doc.id,
            version_number=old_doc.version_number,
            filename=old_doc.filename,
            created_at=old_doc.created_at,
        ),
        new=DiffVersionInfo(
            id=new_doc.id,
            version_number=new_doc.version_number,
            filename=new_doc.filename,
            created_at=new_doc.created_at,
        ),
        rows=result["rows"],
        stats=DiffStats(**result["stats"]),
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    Path(document.storage_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
