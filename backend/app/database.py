from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

connect_args = {}
if settings.resolved_database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 15}

engine = create_engine(
    settings.resolved_database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # 连接失效时自动重连，readiness 之外也多一层兜底
)

if settings.resolved_database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        # WAL：读写不互斥，多进程/多 worker 下更稳；busy_timeout 避免瞬时锁冲突报错
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
