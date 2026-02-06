from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    resolved = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
