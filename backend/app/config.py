"""统一配置入口：所有环境变量 / 密钥 / 路径在此解析，其余模块只读 settings。

设计约定：
- 相对路径一律锚定 backend 根目录（本文件的上上级），与启动时的 CWD 无关，
  避免「从不同目录启动连到不同数据库」的问题。
- DATA_DIR 一键覆盖数据根目录（容器里挂卷用）：设置后数据库与上传文件
  默认落在 <DATA_DIR>/app.db 与 <DATA_DIR>/storage，可用 DATABASE_URL /
  STORAGE_DIR 单独覆盖。
- APP_ENV=production 时收紧默认值（关文档、JSON 日志、不自动迁移），
  并通过 config_warnings() 暴露不安全的生产配置（如默认密钥）。
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_SECRET_KEY = "dev-only-secret-change-me"


def _default(value, fallback):
    return fallback if value is None else value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", ".env"),  # 前者优先兜底，保证与 CWD 无关
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 运行环境 ---
    app_env: Literal["development", "production"] = "development"
    app_name: str = "合同审查协作工具"

    # --- 数据位置 ---
    data_dir: Path | None = None
    database_url: str | None = None  # 默认 sqlite:///<数据根>/app.db
    storage_dir: Path | None = None  # 默认 <数据根>/storage

    # --- 密钥（当前版本未用于签名，预留；生产环境必须覆盖默认值）---
    secret_key: str = DEFAULT_SECRET_KEY

    # --- 网络 / 跨域 ---
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3200", "http://localhost:3000"]
    )
    max_upload_mb: int = 20

    # --- 日志 ---
    log_level: str = "INFO"
    log_format: Literal["json", "text"] | None = None  # 默认 dev=text / prod=json

    # --- 启动行为 ---
    auto_migrate: bool | None = None  # 默认 dev=True / prod=False
    enable_docs: bool | None = None   # 默认 dev=True / prod=False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        """支持逗号分隔字符串或 JSON 数组两种写法。"""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json

                return [str(o).strip() for o in json.loads(v)]
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # ---------- 派生配置 ----------

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def resolved_data_dir(self) -> Path:
        return (self.data_dir or BASE_DIR).resolve()

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            url = self.database_url
            prefix = "sqlite:///"
            if url.startswith(prefix):
                raw = url[len(prefix):]
                p = Path(raw)
                if not p.is_absolute():
                    p = (BASE_DIR / p).resolve()
                return prefix + str(p)
            return url
        return f"sqlite:///{self.resolved_data_dir / 'app.db'}"

    @property
    def resolved_storage_dir(self) -> Path:
        if self.storage_dir is not None:
            p = self.storage_dir
            return p if p.is_absolute() else (BASE_DIR / p).resolve()
        return self.resolved_data_dir / "storage"

    @property
    def resolved_log_format(self) -> str:
        return self.log_format or ("json" if self.is_production else "text")

    @property
    def resolved_auto_migrate(self) -> bool:
        return _default(self.auto_migrate, not self.is_production)

    @property
    def resolved_enable_docs(self) -> bool:
        return _default(self.enable_docs, not self.is_production)

    def config_warnings(self) -> list[str]:
        """生产环境下的不安全配置，启动时以告警形式暴露。"""
        warnings: list[str] = []
        if self.is_production and self.secret_key == DEFAULT_SECRET_KEY:
            warnings.append("SECRET_KEY 仍为默认值，生产环境必须通过环境变量覆盖")
        if self.is_production and not self.cors_origins:
            warnings.append("CORS_ORIGINS 为空：跨域前端将被拒绝（同源部署可忽略）")
        return warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()
