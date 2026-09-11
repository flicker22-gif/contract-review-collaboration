from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Annotation, Reply
from ..schemas import ReplyCreate, ReplyOut

router = APIRouter(tags=["replies"])


@router.post(
    "/api/annotations/{annotation_id}/replies",
    response_model=ReplyOut,
    status_code=201,
)
def create_reply(
    annotation_id: int,
    payload: ReplyCreate,
    db: Session = Depends(get_db),
):
    if not db.get(Annotation, annotation_id):
        raise HTTPException(status_code=404, detail="批注不存在")

    reply = Reply(
        annotation_id=annotation_id,
        author_name=payload.author_name,
        author_role=payload.author_role,
        content=payload.content,
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply
