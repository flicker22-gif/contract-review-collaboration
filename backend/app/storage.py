"""上传文件存储适配层。

业务代码只面向 StorageBackend 协议编程，数据库里只存相对 key（如
``505e8486....docx``），不存任何绝对路径 —— 这样数据目录整体迁移、
容器挂卷、换对象存储都不需要改库。

当前实现：LocalStorage（本地文件系统，原子写入）。
要接 S3/MinIO 时新增一个实现同一协议的类并在 get_storage() 里切换即可，
调用方与数据库内容均无需改动。
"""
import os
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol, runtime_checkable

from .config import get_settings


@runtime_checkable
class StorageBackend(Protocol):
    """文件存储后端协议：以 key 读写删原始文件字节。"""

    def save(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

    def check_writable(self) -> None:
        """不可写时抛异常（readiness 探针依赖此语义）。"""
        ...


class LocalStorage:
    """本地目录存储：写入走 临时文件+rename，避免半截文件被读到。"""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # key 只能是文件名，拒绝路径穿越
        if Path(key).name != key:
            raise ValueError(f"非法存储 key: {key!r}")
        return self.root / key

    def save(self, key: str, data: bytes) -> None:
        target = self._path(key)
        fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def check_writable(self) -> None:
        probe = f".ready-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.save(probe, b"ok")
        self.delete(probe)


@lru_cache
def get_storage() -> StorageBackend:
    return LocalStorage(get_settings().resolved_storage_dir)
