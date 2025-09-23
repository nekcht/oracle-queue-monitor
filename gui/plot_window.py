# gui/plot_window.py
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
import pyqtgraph as pg
from collections import deque
import time
import math


class IntAxis(pg.AxisItem):
    """Left axis that renders integer-only tick labels; spacing can be set."""
    def tickStrings(self, values, scale, spacing):
        return [str(int(round(v))) for v in values]


def _nice_step(vrange, target_ticks=6):
    """Return a 'nice' major step for the given data range."""
    if vrange <= 0 or math.isinf(vrange) or math.isnan(vrange):
        return 1
    raw = vrange / max(1, target_ticks)
    pow10 = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        step = m * pow10
        if raw <= step:
            return step
    return pow10  # fallback


class PlotWindow(QDialog):
    """
    Live plot window:
      - Blue line = actual values (dot on first sample)
      - Yellow dashed line = forecast
      - Red dots = anomalies
      - Integer-only Y axis
      - Legend anchored top-right
      - Top bar shows 'Current:' and lets you change Polling (sec) for THIS plot only
    """
    closed = pyqtSignal()
    poll_changed = pyqtSignal(int)  # emit when user changes polling sec in the plot

    def __init__(self, max_points=500, initial_poll_sec=5, title="Live Record Counts"):
        super().__init__()
        self.setWindowTitle(title)
        res_path = Path(__file__).resolve().parent.parent / "resources"
        self.setWindowIcon(QIcon(str(res_path / "app.png")))
        self.max_points = max_points
        self.t0 = time.time()

        # Buffers
        self.timestamps = deque(maxlen=max_points)
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
        self.poll_spin.valueChanged.connect(lambda v: self.poll_changed.emit(int(v)))
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
            axisItems={'left': IntAxis(orientation='left')}
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

        # Softer, less-dense grid (alpha + we control tick spacing each update)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.12)

        # Labels
        self.plot_widget.setLabel('left', 'Count')
        self.plot_widget.setLabel('bottom', 'Time', units='s')

    def show_info(self, text: str, msec: int = 3000):
        self.info_msg.setText(text)
        self.info_msg.setVisible(True)
        QTimer.singleShot(msec, lambda: self.info_msg.setVisible(False))

    def _retick(self, x_vals):
        """Loosen grid/ticks based on current ranges."""
        pi = self.plot_widget.getPlotItem()

        # Y ticks
        if self.values:
            y_min, y_max = min(self.values), max(self.values)
            if y_min == y_max:
                step_y = 1
            else:
                step_y = _nice_step(y_max - y_min, target_ticks=6)
            self.plot_widget.getAxis('left').setTickSpacing(major=step_y, minor=max(1, step_y/5))

        # X ticks
        if x_vals:
            span = (x_vals[-1] - x_vals[0]) if len(x_vals) > 1 else max(1.0, x_vals[-1])
            step_x = _nice_step(span, target_ticks=6)
            self.plot_widget.getAxis('bottom').setTickSpacing(major=step_x, minor=max(0.5, step_x/5))

    def add_point(self, timestamp, value, is_anomaly=False, forecast=None):
        # Update buffers
        self.timestamps.append(float(timestamp))
        self.values.append(float(value))
        self.anoms.append(bool(is_anomaly))
        self.forecasts.append(float(forecast) if forecast is not None else float('nan'))

        # X axis in seconds since window opened
        x = [t - self.t0 for t in self.timestamps]

        # Update lines
        self.line_actual.setData(x, list(self.values))
        self.line_forecast.setData(x, [fv if fv is not None else float('nan') for fv in self.forecasts])

        # Update anomalies
        pts = [{'pos': (xi, v), 'brush': 'r'} for xi, (v, a) in zip(x, zip(self.values, self.anoms)) if a]
        self.scatter_anom.setData(pts)

        # Y-range handling: if flat, expand slightly; else autorange
        pi = self.plot_widget.getPlotItem()
        y_min = min(self.values)
        y_max = max(self.values)
        if y_min == y_max:
            pad = 1.0
            pi.setYRange(y_min - pad, y_max + pad, padding=0)
        else:
            pi.enableAutoRange(axis='y', enable=True)

        # Retick to relax grid
        self._retick(x)

        # Big "Current" readout
        cur_txt = int(value) if float(value).is_integer() else round(float(value), 2)
        self.current_label.setText(f"Current: {cur_txt}")

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
