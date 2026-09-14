"""document versioning columns

为 documents 增加 group_id / version_number 并回填：旧文档各自成组
（group_id = 'g' || id），版本号从 1 开始。列已存在时跳过，可重复执行。

Revision ID: 0002_document_versioning
Revises: 0001_initial
Create Date: 2026-09-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_document_versioning"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {col["name"] for col in sa.inspect(bind).get_columns("documents")}

    if "group_id" not in existing:
        op.add_column("documents", sa.Column("group_id", sa.String(32), nullable=True))
    if "version_number" not in existing:
        op.add_column(
            "documents",
            sa.Column("version_number", sa.Integer(), nullable=True),
        )

    # 回填：未分组的旧文档各自成组，版本号补 1（幂等：只动 NULL 行）
    bind.execute(
        sa.text("UPDATE documents SET group_id = 'g' || id WHERE group_id IS NULL")
    )
    bind.execute(
        sa.text("UPDATE documents SET version_number = 1 WHERE version_number IS NULL")
    )

    index_names = {ix["name"] for ix in sa.inspect(bind).get_indexes("documents")}
    if "ix_documents_group_id" not in index_names:
        op.create_index("ix_documents_group_id", "documents", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_group_id", table_name="documents")
    op.drop_column("documents", "version_number")
    op.drop_column("documents", "group_id")
