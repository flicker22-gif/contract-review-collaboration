from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .database import Base, engine
from .routers import annotations, documents, replies


def _run_lightweight_migrations() -> None:
    """create_all 不会给已存在的表补列，对旧库手动 ALTER TABLE。"""
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("documents")}
    with engine.begin() as conn:
        if "group_id" not in existing:
            conn.execute(text("ALTER TABLE documents ADD COLUMN group_id VARCHAR(32)"))
            # 旧文档各自成组，用 id 作为 group_id
            conn.execute(text("UPDATE documents SET group_id = 'g' || id"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_group_id ON documents (group_id)"))
        if "version_number" not in existing:
            conn.execute(text("ALTER TABLE documents ADD COLUMN version_number INTEGER DEFAULT 1"))
            conn.execute(text("UPDATE documents SET version_number = 1 WHERE version_number IS NULL"))


_run_lightweight_migrations()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="合同审查协作工具", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3200",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(annotations.router)
app.include_router(replies.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
