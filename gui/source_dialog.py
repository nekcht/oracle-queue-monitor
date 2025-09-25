# gui/source_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QSpinBox,
    QDialogButtonBox, QPlainTextEdit
)
from core.logger import logger


class SourceDialog(QDialog):
    """
    Add/Edit a single source.
    Per-source fields:
      - name, host, port, service_name, user, password
      - polling_frequency (optional, overrides global if >0)
      - query (must return exactly ONE row × ONE numeric column)
    """
    def __init__(self, parent=None, source=None):
        super().__init__(parent)
        self.setWindowTitle("Source")
        self.setModal(True)

        s = source or {}

        root = QVBoxLayout(self)

        # Top grid with connection & optional per-source polling
        g = QGridLayout()
        row = 0

        self.name = QLineEdit(s.get("name", ""))
        self.host = QLineEdit(s.get("host", ""))
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(int(s.get("port", 1521)))
        self.service = QLineEdit(s.get("service_name", ""))
        self.user = QLineEdit(s.get("user", ""))
        self.pwd = QLineEdit(s.get("password", "")); self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.poll = QSpinBox(); self.poll.setRange(0, 3600); self.poll.setValue(int(s.get("polling_frequency", 0) or 0))
        self.poll.setToolTip("0 = use global polling frequency from Settings")

        fields = [
            ("Name:", self.name),
            ("Host:", self.host),
            ("Port:", self.port),
            ("Service Name:", self.service),
            ("User:", self.user),
            ("Password:", self.pwd),
            ("Polling (sec, optional):", self.poll),
        ]
        for label, widget in fields:
            g.addWidget(QLabel(label), row, 0)
            g.addWidget(widget, row, 1)
            row += 1

        root.addLayout(g)

        # Query editor
        root.addWidget(QLabel("Query (must return exactly ONE row with ONE numeric column):"))
        self.query = QPlainTextEdit(s.get("query", ""))
        self.query.setPlaceholderText("e.g. SELECT COUNT(*) FROM MY_SCHEMA.MY_TABLE\n"
                                      "or   SELECT COUNT(*) FROM MY_SCHEMA.MY_TABLE WHERE STATUS = 'ERROR'")
        self.query.setTabChangesFocus(True)
        self.query.setMinimumHeight(90)
        root.addWidget(self.query)

        # Dialog buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_accept(self):
        # minimal validation: name, host, service, user, query
        if not (self.name.text().strip() and self.host.text().strip()
                and self.service.text().strip() and self.user.text().strip()
                and self.query.toPlainText().strip()):
            # Let the parent handle messaging if desired; for now just keep dialog open
            self.setWindowTitle("Source (fill required fields)")
            return
        self.accept()

    def get_data(self):
        data = {
            "name": self.name.text().strip() or "Source",
            "host": self.host.text().strip(),
            "port": int(self.port.value()),
            "service_name": self.service.text().strip(),
            "user": self.user.text().strip(),
            "password": self.pwd.text(),  # keep as entered
            "query": self.query.toPlainText().strip(),
        }
        pf = int(self.poll.value())
        if pf > 0:
            data["polling_frequency"] = pf
        else:
            # ensure we don't persist zero; omit to inherit global setting
            data.pop("polling_frequency", None)
        return data
