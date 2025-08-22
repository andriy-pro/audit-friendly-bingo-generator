from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional

from rich.logging import RichHandler


def setup_logging(*, level: str = "INFO", log_file: Optional[str] = None, json_format: bool = False) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    handlers: List[logging.Handler] = []
    handlers.append(RichHandler(rich_tracebacks=True, show_time=True, show_level=True, markup=True))
    if log_file:
        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setLevel(lvl)
        fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
    logging.basicConfig(level=lvl, handlers=handlers, force=True)


