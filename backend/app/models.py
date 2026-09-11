from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # docx | pdf
    storage_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    paragraphs = relationship(
        "Paragraph", back_populates="document", cascade="all, delete-orphan",
        order_by="Paragraph.idx",
    )
    annotations = relationship(
        "Annotation", back_populates="document", cascade="all, delete-orphan"
    )


class Paragraph(Base):
    __tablename__ = "paragraphs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    idx = Column(Integer, nullable=False)  # 段落在文档中的顺序
    text = Column(Text, nullable=False)

    document = relationship("Document", back_populates="paragraphs")
    annotations = relationship(
        "Annotation", back_populates="paragraph", cascade="all, delete-orphan"
    )


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    paragraph_id = Column(Integer, ForeignKey("paragraphs.id"), nullable=False)
    start_offset = Column(Integer, nullable=False)  # 段内字符偏移（含）
    end_offset = Column(Integer, nullable=False)    # 段内字符偏移（不含）
    quoted_text = Column(Text, nullable=False)      # 冗余存原文，便于展示与校验
    comment = Column(Text, nullable=False)
    author_name = Column(String(64), nullable=False)
    author_role = Column(String(16), nullable=False)  # legal | business
    status = Column(String(16), nullable=False, default="open")  # open | resolved
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="annotations")
    paragraph = relationship("Paragraph", back_populates="annotations")
    replies = relationship(
        "Reply", back_populates="annotation", cascade="all, delete-orphan",
        order_by="Reply.created_at",
    )


class Reply(Base):
    __tablename__ = "replies"

    id = Column(Integer, primary_key=True, index=True)
    annotation_id = Column(Integer, ForeignKey("annotations.id"), nullable=False)
    author_name = Column(String(64), nullable=False)
    author_role = Column(String(16), nullable=False)  # legal | business
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    annotation = relationship("Annotation", back_populates="replies")
