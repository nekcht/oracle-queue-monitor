# gui/settings_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QLineEdit, QPushButton, QFileDialog, QGroupBox, QFormLayout
)

class SettingsDialog(QDialog):
    def __init__(self, parent=None, cfg=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(0,0,0,40);   /* lighter border */
                margin-top: 6px;                   /* space above title */
                padding-top: 6;                 /* extra gap between title and first row */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px 0 3px;
            }
        """)
        cfg = cfg or {}

        root = QVBoxLayout(self)

        # General group
        grp_general = QGroupBox("General")
        form_gen = QFormLayout(grp_general)

        self.win  = QSpinBox(); self.win.setRange(8, 10000); self.win.setValue(int(cfg.get("window_size", 64)))
        self.inst = QLineEdit(str(cfg.get("instant_client_path","")))
        btn_browse = QPushButton("Browse..."); btn_browse.clicked.connect(self._browse)

        form_gen.addRow("Window size:", self.win)
        row = QGridLayout()
        row.addWidget(self.inst, 0, 0)
        row.addWidget(btn_browse, 0, 1)
        form_gen.addRow(QLabel("Instant Client Path:"), row)

        # Anomaly Detector group
        grp_model = QGroupBox("Anomaly Detector (one-sided, adaptive)")
        form_m = QFormLayout(grp_model)

        self.k_upper = QDoubleSpinBox(); self.k_upper.setDecimals(2); self.k_upper.setRange(0.1, 50.0); self.k_upper.setSingleStep(0.1); self.k_upper.setValue(float(cfg.get("k_upper", 3.0)))
        self.min_rel = QDoubleSpinBox(); self.min_rel.setDecimals(2); self.min_rel.setRange(0.0, 10.0); self.min_rel.setSingleStep(0.05); self.min_rel.setValue(float(cfg.get("min_rel_increase", 0.25)))
        self.q = QDoubleSpinBox(); self.q.setDecimals(3); self.q.setRange(0.90, 0.999); self.q.setSingleStep(0.001); self.q.setValue(float(cfg.get("q", 0.995)))
        self.ew_alpha = QDoubleSpinBox(); self.ew_alpha.setDecimals(2); self.ew_alpha.setRange(0.01, 0.99); self.ew_alpha.setSingleStep(0.01); self.ew_alpha.setValue(float(cfg.get("ew_alpha", 0.2)))
        self.debounce = QSpinBox(); self.debounce.setRange(0, 20); self.debounce.setValue(int(cfg.get("debounce", 1)))

        form_m.addRow("k_upper (σ multiplier):", self.k_upper)
        form_m.addRow("min_rel_increase (× forecast):", self.min_rel)
        form_m.addRow("quantile q (pos residuals):", self.q)
        form_m.addRow("EW alpha (residual scale):", self.ew_alpha)
        form_m.addRow("debounce (ticks):", self.debounce)

        # Layout
        root.addWidget(grp_general)
        root.addWidget(grp_model)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Oracle Instant Client Folder")
        if d: self.inst.setText(d)

    def get_values(self):
        return {
            "window_size": int(self.win.value()),
            "instant_client_path": self.inst.text().strip(),
            "k_upper": float(self.k_upper.value()),
            "min_rel_increase": float(self.min_rel.value()),
            "q": float(self.q.value()),
            "ew_alpha": float(self.ew_alpha.value()),
            "debounce": int(self.debounce.value()),
        }
