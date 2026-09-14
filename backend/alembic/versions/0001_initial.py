"""initial schema

在全新数据库上创建全部四张表；对已有旧库（表已存在）自动跳过，
因此同一条 `upgrade head` 命令对新旧库都可重复执行。

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _existing_tables()

    if "documents" not in tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("file_type", sa.String(10), nullable=False),
            sa.Column("storage_path", sa.String(512), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_documents_id", "documents", ["id"])

    if "paragraphs" not in tables:
        op.create_table(
            "paragraphs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("documents.id"),
                nullable=False,
            ),
            sa.Column("idx", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
        )
        op.create_index("ix_paragraphs_id", "paragraphs", ["id"])

    if "annotations" not in tables:
        op.create_table(
            "annotations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("documents.id"),
                nullable=False,
            ),
            sa.Column(
                "paragraph_id",
                sa.Integer(),
                sa.ForeignKey("paragraphs.id"),
                nullable=False,
            ),
            sa.Column("start_offset", sa.Integer(), nullable=False),
            sa.Column("end_offset", sa.Integer(), nullable=False),
            sa.Column("quoted_text", sa.Text(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=False),
            sa.Column("author_name", sa.String(64), nullable=False),
            sa.Column("author_role", sa.String(16), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_annotations_id", "annotations", ["id"])

    if "replies" not in tables:
        op.create_table(
            "replies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "annotation_id",
                sa.Integer(),
                sa.ForeignKey("annotations.id"),
                nullable=False,
            ),
            sa.Column("author_name", sa.String(64), nullable=False),
            sa.Column("author_role", sa.String(16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_replies_id", "replies", ["id"])


def downgrade() -> None:
    for table in ("replies", "annotations", "paragraphs", "documents"):
        op.drop_table(table)
