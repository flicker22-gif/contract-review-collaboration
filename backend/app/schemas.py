from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

AuthorRole = Literal["legal", "business"]
AnnotationStatus = Literal["open", "resolved"]


# ---------- Paragraph ----------

class ParagraphOut(BaseModel):
    id: int
    idx: int
    text: str

    class Config:
        from_attributes = True


# ---------- Reply ----------

class ReplyCreate(BaseModel):
    author_name: str = Field(min_length=1, max_length=64)
    author_role: AuthorRole
    content: str = Field(min_length=1)


class ReplyOut(BaseModel):
    id: int
    annotation_id: int
    author_name: str
    author_role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Annotation ----------

class AnnotationCreate(BaseModel):
    paragraph_id: int
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    comment: str = Field(min_length=1)
    author_name: str = Field(min_length=1, max_length=64)
    author_role: AuthorRole


class AnnotationUpdate(BaseModel):
    status: AnnotationStatus


class AnnotationOut(BaseModel):
    id: int
    document_id: int
    paragraph_id: int
    start_offset: int
    end_offset: int
    quoted_text: str
    comment: str
    author_name: str
    author_role: str
    status: str
    created_at: datetime
    replies: List[ReplyOut] = []

    class Config:
        from_attributes = True


# ---------- Document ----------

class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    group_id: str | None = None
    version_number: int = 1
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListItem(DocumentOut):
    annotation_count: int
    open_count: int


class DocumentDetail(DocumentOut):
    paragraphs: List[ParagraphOut] = []


# ---------- Version / Diff ----------

class VersionOut(BaseModel):
    id: int
    version_number: int
    filename: str
    file_type: str
    created_at: datetime
    annotation_count: int
    open_count: int

    class Config:
        from_attributes = True


class DiffToken(BaseModel):
    op: Literal["equal", "insert", "delete"]
    v: str


class DiffRow(BaseModel):
    type: Literal["equal", "modified", "deleted", "added"]
    old_idx: int | None
    new_idx: int | None
    text: str | None = None
    old_text: str | None = None
    new_text: str | None = None
    old_tokens: List[DiffToken] = []
    new_tokens: List[DiffToken] = []


class DiffStats(BaseModel):
    added: int
    deleted: int
    modified: int
    unchanged: int
    added_chars: int
    deleted_chars: int


class DiffVersionInfo(BaseModel):
    id: int
    version_number: int
    filename: str
    created_at: datetime


class DiffResponse(BaseModel):
    old: DiffVersionInfo
    new: DiffVersionInfo
    rows: List[DiffRow]
    stats: DiffStats
