from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Annotation, Document, Paragraph
from ..schemas import AnnotationCreate, AnnotationOut, AnnotationUpdate

router = APIRouter(tags=["annotations"])


@router.get(
    "/api/documents/{document_id}/annotations",
    response_model=list[AnnotationOut],
)
def list_annotations(document_id: int, db: Session = Depends(get_db)):
    if not db.get(Document, document_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return (
        db.query(Annotation)
        .options(joinedload(Annotation.replies))
        .filter(Annotation.document_id == document_id)
        .order_by(Annotation.created_at)
        .all()
    )


@router.post(
    "/api/documents/{document_id}/annotations",
    response_model=AnnotationOut,
    status_code=201,
)
def create_annotation(
    document_id: int,
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
):
    if not db.get(Document, document_id):
        raise HTTPException(status_code=404, detail="文档不存在")

    paragraph = db.get(Paragraph, payload.paragraph_id)
    if not paragraph or paragraph.document_id != document_id:
        raise HTTPException(status_code=400, detail="段落不属于该文档")

    if payload.end_offset > len(paragraph.text):
        raise HTTPException(status_code=400, detail="高亮范围超出段落长度")

    quoted_text = paragraph.text[payload.start_offset:payload.end_offset]

    annotation = Annotation(
        document_id=document_id,
        paragraph_id=payload.paragraph_id,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        quoted_text=quoted_text,
        comment=payload.comment,
        author_name=payload.author_name,
        author_role=payload.author_role,
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.patch("/api/annotations/{annotation_id}", response_model=AnnotationOut)
def update_annotation(
    annotation_id: int,
    payload: AnnotationUpdate,
    db: Session = Depends(get_db),
):
    annotation = db.get(Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="批注不存在")
    annotation.status = payload.status
    db.commit()
    db.refresh(annotation)
    return annotation


@router.delete("/api/annotations/{annotation_id}", status_code=204)
def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    annotation = db.get(Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="批注不存在")
    db.delete(annotation)
    db.commit()
