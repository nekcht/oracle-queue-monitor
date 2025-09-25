import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

_file = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
_file.setFormatter(_formatter)
_file.setLevel(logging.INFO)

_console = logging.StreamHandler()
_console.setFormatter(_formatter)
_console.setLevel(logging.INFO)

logger = logging.getLogger("oracle_monitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(_file)
    logger.addHandler(_console)
logger.propagate = False
