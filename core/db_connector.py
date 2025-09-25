import os
import oracledb
from core.logger import logger

class DBConnector:
    def __init__(self, host, port, service_name, user, password, instant_client_path=None):
        self.host = host
        self.port = port
        self.service_name = service_name
        self.user = user
        self.password = password
        self.instant_client_path = instant_client_path
        self.conn = None

        try:
            if self.instant_client_path and os.path.isdir(self.instant_client_path):
                oracledb.init_oracle_client(lib_dir=self.instant_client_path)
                logger.info(f"Oracle Instant Client initialized from {self.instant_client_path}")
            else:
                logger.info("Using Thin mode (no Instant Client)")
        except Exception as e:
            logger.warning(f"Failed to initialize Thick mode: {e}. Falling back to Thin mode.")

    def connect(self):
        dsn = f"{self.host}:{self.port}/{self.service_name}"
        logger.info(f"DB connect | dsn={dsn} user={self.user}")
        self.conn = oracledb.connect(user=self.user, password=self.password, dsn=dsn)
        logger.info("DB connected")
        return self.conn

    def close(self):
        if self.conn:
            try:
                self.conn.close()
                logger.info("DB connection closed")
            except Exception as e:
                logger.warning(f"DB close error: {e}")
            self.conn = None

    def execute_scalar(self, query: str):
        if not self.conn:
            self.connect()
        cur = self.conn.cursor()
        try:
            logger.debug(f"DB execute | {query}")
            cur.execute(query)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Query returned no rows")
            val = row[0]
            logger.info(f"DB scalar result | {val}")
            return val
        finally:
            try:
                cur.close()
            except Exception:
                pass
