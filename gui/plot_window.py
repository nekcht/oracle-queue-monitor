# gui/plot_window.py
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
import pyqtgraph as pg
from collections import deque
import time
import math
from core.logger import logger


class IntAxis(pg.AxisItem):
    """Left axis that renders integer-only tick labels; spacing can be set."""
    def tickStrings(self, values, scale, spacing):
        return [str(int(round(v))) for v in values]


class ClockAxis(pg.AxisItem):
    """Bottom axis: UNIX timestamps -> local 'HH:MM'. Disables SI prefixes."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.enableAutoSIPrefix(False)
        except Exception:
            pass

    @staticmethod
    def _fmt(ts: float) -> str:
        tm = time.localtime(ts)
        return time.strftime("%H:%M", tm)

    def tickStrings(self, values, scale, spacing):
        return [self._fmt(v) for v in values]


def _nice_minute_step(span_sec: float, target_ticks=6) -> int:
    """Pick a 'nice' minute-based step (in seconds) for the given span (seconds)."""
    if span_sec <= 0 or math.isinf(span_sec) or math.isnan(span_sec):
        return 60
    raw = span_sec / max(1, target_ticks)
    # prefer minute-ish steps
    candidates = [
        30, 60, 120, 300, 600, 900, 1200, 1800, 3600, 7200
    ]  # 30s, 1m, 2m, 5m, 10m, 15m, 20m, 30m, 1h, 2h
    for step in candidates:
        if raw <= step:
            return step
    # fallback larger steps
    return int(max(3600, round(raw / 300) * 300))  # multiples of 5m


class PlotWindow(QDialog):
    """
    Live plot window:
      - Blue line = actual values (dot on first sample)
      - Yellow dashed line = forecast
      - Red dots = anomalies
      - Left axis integer-only
      - Bottom axis shows local time 'HH:MM'
      - Legend top-right
      - Top bar shows 'Current:' and per-plot Polling (sec)
    """
    closed = pyqtSignal()
    poll_changed = pyqtSignal(int)  # emitted when user changes polling sec in the plot

    def __init__(self, max_points=500, initial_poll_sec=5, title="Live Record Counts"):
        super().__init__()
        self.setWindowTitle(title)
        res_path = Path(__file__).resolve().parent.parent / "resources"
        self.setWindowIcon(QIcon(str(res_path / "app.png")))
        self.max_points = max_points

        # Buffers
        self.timestamps = deque(maxlen=max_points)  # UNIX seconds
        self.values = deque(maxlen=max_points)
        self.anoms = deque(maxlen=max_points)
        self.forecasts = deque(maxlen=max_points)

        root = QVBoxLayout(self)

        # Top bar: Current value + Polling control
        top = QHBoxLayout()
        self.current_label = QLabel("Current: -")
        self.current_label.setFont(QFont("Arial", 11, QFont.Weight.DemiBold))
        top.addWidget(self.current_label)
        top.addStretch(1)

        top.addWidget(QLabel("Polling (s):"))
        self.poll_spin = QSpinBox()
        self.poll_spin.setRange(1, 3600)
        self.poll_spin.setValue(int(initial_poll_sec or 5))
        self.poll_spin.valueChanged.connect(self._on_poll_changed)

        top.addWidget(self.poll_spin)
        root.addLayout(top)

        self.info_msg = QLabel("")
        self.info_msg.setStyleSheet("color: #666; font-size: 11px;")
        self.info_msg.setVisible(False)
        root.addWidget(self.info_msg)

        # Plot widget
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget(
            background='w',
            title=title,
            axisItems={
                'left':   IntAxis(orientation='left'),
                'bottom': ClockAxis(orientation='bottom')
            }
        )
        root.addWidget(self.plot_widget)

        legend = self.plot_widget.addLegend()
        legend.setParentItem(self.plot_widget.getPlotItem().getViewBox())
        legend.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-10, 10))

        # Axis tick font
        self.plot_widget.getAxis('left').setTickFont(QFont("Arial", 9))
        self.plot_widget.getAxis('bottom').setTickFont(QFont("Arial", 9))

        # Lines
        self.line_actual = self.plot_widget.plot(
            [], [], pen=pg.mkPen(color=(0, 122, 204), width=2),
            name="Actual",
            symbol='o', symbolSize=6, symbolBrush=(0, 122, 204)  # show first point
        )
        self.line_forecast = self.plot_widget.plot(
            [], [], pen=pg.mkPen(color=(255, 215, 0), width=2, style=Qt.PenStyle.DashLine),
            name="Forecast"
        )

        # Scatter for anomalies
        self.scatter_anom = pg.ScatterPlotItem(size=10, brush='r', pen=pg.mkPen(width=0))
        self.plot_widget.addItem(self.scatter_anom)

        # Softer grid
        self.plot_widget.showGrid(x=True, y=True, alpha=0.12)

        # Labels
        self.plot_widget.setLabel('left', 'Count')
        self.plot_widget.setLabel('bottom', 'Time (HH:MM)')

    def show_info(self, text: str, msec: int = 3000):
        self.info_msg.setText(text)
        self.info_msg.setVisible(True)
        QTimer.singleShot(msec, lambda: self.info_msg.setVisible(False))

    def _on_poll_changed(self, v: int):
        # show message only in THIS window
        self.show_info(f"Polling will change to {int(v)}s after the current cycle.")
        # then emit to whoever is listening (main window/worker)
        self.poll_changed.emit(int(v))
        logger.info(f"Plot polling change -> {int(v)}s")

    def _retick(self, x_ts):
        """Relax grid/ticks based on current time span (in seconds)."""
        # Y ticks
        if self.values:
            y_min, y_max = min(self.values), max(self.values)
            step_y = 1 if y_min == y_max else max(1, int(round((y_max - y_min) / 6)) or 1)
            self.plot_widget.getAxis('left').setTickSpacing(major=step_y, minor=max(1, step_y // 5))

        # X ticks: choose nice minute-based step
        if x_ts:
            span = (x_ts[-1] - x_ts[0]) if len(x_ts) > 1 else 60.0
            step_x = _nice_minute_step(span, target_ticks=6)
            self.plot_widget.getAxis('bottom').setTickSpacing(major=step_x, minor=max(60, step_x // 5 or 60))

    def add_point(self, timestamp, value, is_anomaly=False, forecast=None):
        # Update buffers (timestamp is UNIX seconds from controller)
        self.timestamps.append(float(timestamp))
        self.values.append(float(value))
        self.anoms.append(bool(is_anomaly))
        self.forecasts.append(float(forecast) if forecast is not None else float('nan'))

        x = list(self.timestamps)  # real timestamps on X

        # Update lines
        self.line_actual.setData(x, list(self.values))
        self.line_forecast.setData(x, [fv if fv is not None else float('nan') for fv in self.forecasts])

        # Update anomalies
        pts = [{'pos': (xi, v), 'brush': 'r'} for xi, (v, a) in zip(x, zip(self.values, self.anoms)) if a]
        self.scatter_anom.setData(pts)

        # Y-range handling
        pi = self.plot_widget.getPlotItem()
        y_min = min(self.values)
        y_max = max(self.values)
        if y_min == y_max:
            pad = 1.0
            pi.setYRange(y_min - pad, y_max + pad, padding=0)
        else:
            pi.enableAutoRange(axis='y', enable=True)

        # Retick for cleaner grid
        self._retick(x)

        # Current value readout
        cur_txt = int(value) if float(value).is_integer() else round(float(value), 2)
        self.current_label.setText(f"Current: {cur_txt}")
        logger.debug(f"Plot add_point | ts={timestamp} val={value} anom={is_anomaly} fc={forecast}")

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
