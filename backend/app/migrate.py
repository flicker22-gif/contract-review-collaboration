"""正式迁移入口：``python -m app.migrate``。

用法：
    python -m app.migrate            # 升级到最新版本（幂等，可重复执行）
    python -m app.migrate --check    # 已在最新版则退出码 0，否则 1（供探针/CI）
    python -m app.migrate --current  # 打印当前版本与最新版本

容器启动链路（docker-entrypoint.sh）先执行本命令再拉起服务；
应用 readiness 探针复用 migration_status() 校验版本一致。
"""
import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def migration_status() -> tuple[str | None, str]:
    """返回 (数据库当前版本, 代码最新版本)。未初始化时当前版本为 None。"""
    from .database import engine

    cfg = alembic_config()
    heads = ScriptDirectory.from_config(cfg).get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"迁移版本存在多个 head: {heads}")
    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
    return current, heads[0]


def run_migrations() -> None:
    command.upgrade(alembic_config(), "head")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.migrate")
    parser.add_argument("--check", action="store_true", help="仅校验是否已是最新")
    parser.add_argument("--current", action="store_true", help="打印版本状态")
    args = parser.parse_args(argv)

    if args.check:
        current, head = migration_status()
        if current != head:
            print(f"数据库迁移未完成: current={current!r} head={head!r}", file=sys.stderr)
            return 1
        print(f"数据库已是最新: {head}")
        return 0

    if args.current:
        current, head = migration_status()
        print(f"current={current!r} head={head!r}")
        return 0 if current == head else 1

    run_migrations()
    current, head = migration_status()
    print(f"迁移完成: {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
