# core/db_connector.py
import os
import re
import threading
from numbers import Number
import oracledb

IDENT_OK = re.compile(r'^[A-Za-z_][A-Za-z0-9_$.]*$')  # schema.table allowed

def _safe_ident(s: str) -> str:
    if not s or not IDENT_OK.match(s):
        raise ValueError(f"Invalid identifier: {s!r}")
    return s

# Global, idempotent Oracle init (thread-safe)
_ORACLE_LOCK = threading.Lock()
_ORACLE_INIT_DIR = None
def _ensure_oracle_client(lib_dir: str | None):
    """Init Thick mode once per process; ignore subsequent different paths."""
    global _ORACLE_INIT_DIR
    if not lib_dir:
        # Explicitly request Thin mode (do nothing)
        return
    if not os.path.isdir(lib_dir):
        print(f"[WARN] Instant Client path not found: {lib_dir}. Using Thin mode.")
        return
    with _ORACLE_LOCK:
        if _ORACLE_INIT_DIR is None:
            try:
                oracledb.init_oracle_client(lib_dir=lib_dir)
                _ORACLE_INIT_DIR = lib_dir
                print(f"[INFO] Oracle Thick mode initialized from {lib_dir}")
            except Exception as e:
                print(f"[WARN] Failed Thick init ({e}); using Thin mode.")
        elif _ORACLE_INIT_DIR != lib_dir:
            print(f"[WARN] Oracle client already initialized from {_ORACLE_INIT_DIR}; "
                  f"ignoring different path {lib_dir}. Keeping current mode.")


class DBConnector:
    def __init__(self, host, port, service_name, user, password, instant_client_path=None):
        self.host = host
        self.port = port
        self.service_name = service_name
        self.user = user
        self.password = password
        self.instant_client_path = instant_client_path or ""
        self.conn = None

    def connect(self):
        if self.conn:
            return self.conn
        _ensure_oracle_client(self.instant_client_path)
        dsn = f"{self.host}:{self.port}/{self.service_name}"
        self.conn = oracledb.connect(user=self.user, password=self.password, dsn=dsn)
        return self.conn

    def close(self):
        if self.conn:
            try: self.conn.close()
            except Exception: pass
            self.conn = None

    def execute_scalar(self, query: str):
        """Execute a user-provided SQL expected to return exactly one row and one column."""
        self.connect()
        cur = self.conn.cursor()
        try:
            cur.execute(query)
            row1 = cur.fetchone()
            if row1 is None:
                raise ValueError("Query returned no rows.")
            if len(row1) != 1:
                raise ValueError("Query must return exactly ONE column.")
            row2 = cur.fetchone()
            if row2 is not None:
                raise ValueError("Query must return exactly ONE row.")
            val = row1[0]
            if not isinstance(val, Number):
                # try to coerce numeric strings
                try:
                    val = float(val)
                except Exception:
                    raise ValueError("Returned value is not numeric.")
            return val
        finally:
            cur.close()
