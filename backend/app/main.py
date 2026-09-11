from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import annotations, documents, replies

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
