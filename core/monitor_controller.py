# core/monitor_controller.py
from PyQt6.QtCore import QObject
from core.db_connector import DBConnector
from core.anomaly_detector import AnomalyDetector
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
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
        self._freq_changed = False  # realign schedule after change

    @pyqtSlot(int)
    def set_freq(self, new_freq: int):
        """Thread-safe: can be called from GUI thread; queued to worker thread."""
        self.freq_s = max(1, int(new_freq))
        self._freq_changed = True

    def run(self):
        # immediate first run, then fixed cadence using monotonic time
        next_time = time.monotonic()
        while self._running:
            try:
                val = self.db.execute_scalar(self.query)
                cnt = int(val) if float(val).is_integer() else float(val)
                ts = float(time.time())
                is_anom, forecast = self.detector.add_and_predict(cnt)
                self.tick.emit(ts, int(cnt), bool(is_anom), (None if forecast is None else float(forecast)))
            except Exception as e:
                self.error.emit(f"[{self.source_name}] {e}")

            # schedule next tick
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

    def stop(self):
        self._running = False


class MonitorController(QObject):
    def __init__(self, app_config, source_cfg, update_callback=None, error_callback=None):
        super().__init__()
        self.app_config = app_config
        self.source_cfg = source_cfg
        self.update_callback = update_callback
        self.error_callback = error_callback
        self.db = None; self.worker = None
        self.source_name = source_cfg.get('name', 'Source')

        cfg = app_config.data
        self.detector = AnomalyDetector(
            window_size=int(cfg.get('window_size', 64)),
            k_upper=float(cfg.get('k_upper', 3.0)),
            min_rel_increase=float(cfg.get('min_rel_increase', 0.25)),
            q=float(cfg.get('q', 0.995)),
            ew_alpha=float(cfg.get('ew_alpha', 0.2)),
            debounce=int(cfg.get('debounce', 1)),
        )

    def start(self):
        cfg = self.source_cfg
        freq = int(cfg.get('polling_frequency') or self.app_config.get('polling_frequency') or 5)

        self.db = DBConnector(
            host=cfg['host'], port=cfg['port'], service_name=cfg['service_name'],
            user=cfg['user'], password=cfg['password'],
            instant_client_path=self.app_config.get('instant_client_path') or ""
        )
        self.worker = Worker(
            db=self.db, query=cfg['query'], detector=self.detector,
            freq_s=freq, source_name=self.source_name
        )
        self.worker.tick.connect(lambda ts, c, a, f: self.update_callback and self.update_callback(ts, c, a, f))
        self.worker.error.connect(lambda msg: self.error_callback and self.error_callback(msg))
        self.worker.start()

    def stop(self):
        if self.worker:
            self.worker.stop(); self.worker.wait(); self.worker = None
        if self.db:
            self.db.close(); self.db = None
