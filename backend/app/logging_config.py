"""结构化日志：生产默认 JSON 单行，开发用可读文本；请求日志带 request_id。"""
import json
import logging
import logging.config
from datetime import datetime, timezone

RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in RESERVED and not key.startswith("_"):
                try:
                    json.dumps(value)
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = str(value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str, fmt: str) -> None:
    formatter = "json" if fmt == "json" else "text"
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": JsonFormatter},
                "text": {
                    "format": "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                }
            },
            "root": {"level": level, "handlers": ["default"]},
            "loggers": {
                # uvicorn 自带 handler，避免与 root 重复输出
                "uvicorn": {"handlers": [], "propagate": True},
                "uvicorn.error": {"handlers": [], "propagate": True},
                # 访问日志由 log_requests 中间件统一输出（带 request_id），关掉 uvicorn 的
                "uvicorn.access": {"handlers": [], "propagate": False, "level": "WARNING"},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
