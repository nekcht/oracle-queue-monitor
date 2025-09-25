from PyQt6.QtCore import QObject, QTimer, QThread, pyqtSignal, pyqtSlot
from core.db_connector import DBConnector
from core.anomaly_detector import AnomalyDetector
from core.logger import logger
import time

class Worker(QThread):
    tick = pyqtSignal(float, int, bool, object)
    error = pyqtSignal(str)

    def __init__(self, db, query: str, detector, freq_s: int, source_name: str):
        super().__init__()
        self.db = db
        self.query = query
        self.detector = detector
        self.freq_s = max(1, int(freq_s))
        self.source_name = source_name
        self._running = True
        self._freq_changed = False

    @pyqtSlot(int)
    def set_freq(self, new_freq: int):
        self.freq_s = max(1, int(new_freq))
        self._freq_changed = True
        logger.info(f"[{self.source_name}] Polling change requested: {self.freq_s}s")

    def run(self):
        logger.info(f"[{self.source_name}] Worker started | freq={self.freq_s}s")
        next_time = time.monotonic()
        while self._running:
            try:
                val = self.db.execute_scalar(self.query)
                cnt = int(val) if float(val).is_integer() else float(val)
                ts = float(time.time())
                is_anom, forecast = self.detector.add_and_predict(cnt)
                if is_anom:
                    logger.warning(f"[{self.source_name}] Anomaly | value={cnt} forecast={forecast}")
                self.tick.emit(ts, int(cnt), bool(is_anom), (None if forecast is None else float(forecast)))
            except Exception as e:
                msg = f"[{self.source_name}] {e}"
                logger.exception(msg)
                self.error.emit(msg)

            next_time += self.freq_s
            now = time.monotonic()
            if self._freq_changed or next_time <= now:
                next_time = now + self.freq_s
                self._freq_changed = False

            delay_ms = int(max(0.0, (next_time - now)) * 1000)
            while self._running and delay_ms > 0:
                step = min(200, delay_ms)
                self.msleep(step)
                delay_ms -= step
        logger.info(f"[{self.source_name}] Worker stopped")

    def stop(self):
        logger.info(f"[{self.source_name}] Stop requested")
        self._running = False


class MonitorController(QObject):
    def __init__(self, app_config, source_cfg, update_callback=None, error_callback=None):
        super().__init__()
        self.config = app_config
        self.source = source_cfg
        self.update_callback = update_callback
        self.error_callback = error_callback
        self.db = None
        self.detector = AnomalyDetector(
            window_size=int(self.config.get('window_size') or 20),
            k_upper=float(self.config.get('k_upper') or 3.0)
        )
        self.worker = None

    def start(self):
        s = self.source
        logger.info(f"Start source | { {k: (v if k!='password' else '***') for k,v in s.items()} }")
        self.db = DBConnector(
            s.get('host'), s.get('port'), s.get('service_name'),
            s.get('user'), s.get('password'),
            instant_client_path=self.config.get('instant_client_path')
        )
        self.worker = Worker(
            db=self.db,
            query=s.get('query', ''),
            detector=self.detector,
            freq_s=int(s.get('polling_frequency') or 5),
            source_name=s.get('name', 'Source')
        )
        self.worker.tick.connect(self._on_tick)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def stop(self):
        logger.info("Stop source requested")
        try:
            if self.worker:
                self.worker.stop()
                self.worker.wait(2000)
        finally:
            if self.db:
                self.db.close()
            self.worker = None
            self.db = None

    def _on_tick(self, ts, cnt, is_anom, forecast):
        if self.update_callback:
            try:
                self.update_callback(ts, cnt, is_anom, forecast)
            except Exception as e:
                logger.exception(f"Update callback error: {e}")

    def _on_error(self, msg: str):
        logger.error(msg)
        if self.error_callback:
            try:
                self.error_callback(msg)
            except Exception:
                logger.exception("Error callback failed")
