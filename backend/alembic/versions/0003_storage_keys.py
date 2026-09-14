"""storage_path -> 相对存储 key

旧库把上传文件的绝对路径（如 /home/dev/backend/storage/xxx.docx）写进
documents.storage_path，换机器/进容器后全部失效。本迁移把含目录分隔符
的值统一收敛为纯文件名 key，文件定位交给存储适配层按配置解析。
已是纯 key 的行不动，可重复执行。

Revision ID: 0003_storage_keys
Revises: 0002_document_versioning
Create Date: 2026-09-14
"""
from pathlib import PurePath
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_storage_keys"
down_revision: Union[str, None] = "0002_document_versioning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, storage_path FROM documents")).fetchall()
    for doc_id, storage_path in rows:
        # 同时兼容 POSIX / Windows 风格分隔符
        normalized = str(storage_path).replace("\\", "/")
        key = PurePath(normalized).name
        if key != storage_path:
            bind.execute(
                sa.text("UPDATE documents SET storage_path = :key WHERE id = :id"),
                {"key": key, "id": doc_id},
            )


def downgrade() -> None:
    # 无法从 key 还原旧机器的绝对路径，且还原也没有意义；保留 key 即可。
    pass
