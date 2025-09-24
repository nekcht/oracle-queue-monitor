# gui/main_window.py
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QPixmap
from core import __version__
from core.config_manager import AppConfig
from core.monitor_controller import MonitorController
from gui.plot_window import PlotWindow
from gui.source_dialog import SourceDialog
from gui.settings_dialog import SettingsDialog
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QStatusBar,
    QMenuBar, QToolBar, QTreeWidget, QTreeWidgetItem, QMessageBox
)
from functools import partial


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(430)
        self.setWindowTitle(f"Oracle Monitor v{__version__}")

        # Titlebar: disable maximize, keep minimize/close
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        # App icon
        res_path = Path(__file__).resolve().parent.parent / "resources"
        self.setWindowIcon(QIcon(str(res_path / "app.png")))

        # Core state
        self.config = AppConfig()
        self.controllers = {}  # sid -> MonitorController
        self.plots = {}  # sid -> PlotWindow

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        # UI
        self._init_ui()

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()

        self._left_pad = 10
        self.menuBar().setStyleSheet(f"QMenuBar {{ padding-left: {self._left_pad}px; }}")
        for tb in self.findChildren(QToolBar):
            tb.setStyleSheet(f"QToolBar {{ padding-left: {self._left_pad}px; }}")
            tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.centralWidget().layout().setContentsMargins(self._left_pad, self._left_pad, self._left_pad, self._left_pad)

        self._refresh_sources_view()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        central.setLayout(layout)

        # Header row with label
        header = QHBoxLayout()
        header.addWidget(QLabel("Sources"))
        header.addStretch(1)
        layout.addLayout(header)

        # Sources list
        self.source_tree = QTreeWidget()
        # Removed Query column here
        self.source_tree.setHeaderLabels(["Name", "Host", "Service", "Poll(s)"])
        self.source_tree.setRootIsDecorated(False)
        self.source_tree.setAlternatingRowColors(True)
        self.source_tree.setSelectionMode(self.source_tree.SelectionMode.SingleSelection)
        self.source_tree.itemDoubleClicked.connect(self._edit_selected_source)
        self.source_tree.itemSelectionChanged.connect(self._on_source_selection_changed)
        layout.addWidget(self.source_tree)

    def _create_actions(self):
        res = Path(__file__).resolve().parent.parent / "resources"

        # Run actions
        self.act_start = QAction(QIcon(str(res / "start.png")), "Start", self)
        self.act_start.triggered.connect(self.on_start)

        self.act_stop = QAction(QIcon(str(res / "stop.png")), "Stop", self)
        self.act_stop.triggered.connect(self.on_stop)
        self.act_stop.setEnabled(False)

        # Sources actions
        self.act_add_source = QAction("+ Add Source", self)
        self.act_add_source = QAction(QIcon(str(res / "add.png")), "Add", self)
        self.act_add_source.triggered.connect(self._add_source)

        self.act_remove_source = QAction("− Remove Source", self)
        self.act_remove_source = QAction(QIcon(str(res / "remove.png")), "Remove", self)
        self.act_remove_source.triggered.connect(self._remove_selected_source)
        self.act_remove_source.setEnabled(False)

        # Settings
        self.act_settings = QAction("Settings", self)
        self.act_settings.triggered.connect(self._open_settings_dialog)

        # File / Help
        self.act_exit = QAction("Exit", self)
        self.act_exit.triggered.connect(self.close)

        self.act_about = QAction("About", self)
        self.act_about.triggered.connect(self._show_about)

    def _create_menu_bar(self):
        menubar: QMenuBar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.act_exit)

        run_menu = menubar.addMenu("&Run")
        run_menu.addAction(self.act_start)
        run_menu.addAction(self.act_stop)

        src_menu = menubar.addMenu("&Sources")
        src_menu.addAction(self.act_add_source)
        src_menu.addAction(self.act_remove_source)

        settings_menu = menubar.addMenu("&Settings")
        settings_menu.addAction(self.act_settings)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.act_about)

    def _create_tool_bar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction(self.act_start)
        tb.addAction(self.act_stop)
        tb.addSeparator()
        tb.addAction(self.act_add_source)
        tb.addAction(self.act_remove_source)

    def _refresh_sources_view(self):
        self.source_tree.clear()
        sources = self.config.get("sources") or []
        for i, s in enumerate(sources):
            poll = s.get("polling_frequency")
            poll_txt = str(poll) if poll else ""  # blank => uses global
            item = QTreeWidgetItem([
                s.get("name", ""),
                s.get("host", ""),
                s.get("service_name", ""),
                poll_txt
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            self.source_tree.addTopLevelItem(item)
        self._on_source_selection_changed()

    def _on_source_selection_changed(self):
        has_sel = bool(self.source_tree.selectedItems())
        self.act_remove_source.setEnabled(has_sel)

    def _add_source(self):
        dlg = SourceDialog(self)
        if dlg.exec():
            s = dlg.get_data()
            self.config.data.setdefault("sources", []).append(s)
            self.config.save()
            self._refresh_sources_view()

    def _edit_selected_source(self, item):
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        sources = self.config.get("sources") or []
        if idx is None or idx >= len(sources):
            return
        dlg = SourceDialog(self, source=sources[idx])
        if dlg.exec():
            sources[idx] = dlg.get_data()
            self.config.save()
            self._refresh_sources_view()
            # live update polling if running
            ctrl = self.controllers.get(idx)
            if ctrl:
                new_freq = int(sources[idx].get("polling_frequency") or self.config.get("polling_frequency") or 5)
                try:
                    ctrl.worker.freq_s = new_freq
                    ctrl.worker._freq_changed = True
                    self.status_bar.showMessage(f"Updated polling for '{sources[idx].get('name')}' to {new_freq}s.", 5000)
                except Exception:
                    pass

    def _remove_selected_source(self):
        items = self.source_tree.selectedItems()
        if not items:
            return
        item = items[0]
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        sources = self.config.get("sources") or []
        if idx is None or idx >= len(sources):
            return
        name = sources[idx].get("name", f"Source {idx+1}")
        ret = QMessageBox.question(
            self, "Remove Source",
            f"Remove source '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        # Stop if running
        if idx in self.controllers:
            self._stop_source(idx)

        del sources[idx]
        self.config.save()
        self._refresh_sources_view()

    def on_start(self):
        sources = self.config.get("sources") or []
        if not sources:
            QMessageBox.warning(self, "No Sources", "Add at least one source.")
            return

        # Validate queries present
        empty_q = [s.get("name", "(unnamed)") for s in sources if not (s.get("query") or "").strip()]
        if empty_q:
            QMessageBox.warning(self, "Missing Query", f"Sources with empty query: {', '.join(empty_q)}")
            return

        # Sync actions
        self.act_start.setEnabled(False)
        self.act_stop.setEnabled(True)

        # Start each source (one plot window per source)
        for i, s in enumerate(sources):
            sid = i
            if sid in self.controllers:
                continue  # already running

            current_freq = int(s.get("polling_frequency") or 5)

            plot = PlotWindow(initial_poll_sec=current_freq, title=f"Live: {s.get('name', 'Source')}")
            plot.closed.connect(lambda sid=sid: self._stop_source(sid))
            plot.show()
            self.plots[sid] = plot

            ctrl = MonitorController(
                app_config=self.config,
                source_cfg=s,
                update_callback=lambda ts, c, a, f, sid=sid: self._on_point(sid, ts, c, a, f),
                error_callback=self.on_error
            )
            ctrl.start()

            plot.poll_changed.connect(ctrl.worker.set_freq)
            plot.poll_changed.connect(partial(self._status_poll_msg, s.get('name', 'Source')))

            # also show messages (both in main bar and inside the plot)
            plot.poll_changed.connect(
                lambda newf, name=s.get('name', 'Source'), p=plot:
                self._on_plot_poll_change(name, newf, p)
            )

            # Set initial freq and wire plot → worker directly
            try:
                ctrl.worker.set_freq(current_freq)  # ensure initial
                plot.poll_changed.connect(ctrl.worker.set_freq)  # <-- QUEUED to worker thread
            except Exception:
                pass

            self.controllers[sid] = ctrl

    def _on_plot_poll_change(self, name: str, new_freq: int, plot):
        # main window status bar
        self.status_bar.showMessage(
            f"Polling for '{name}' will change to {new_freq}s after the current cycle finishes.",
            5000
        )
        # inline message inside the plot window
        try:
            plot.show_info(f"Polling will change to {new_freq}s after current cycle.")
        except Exception:
            pass

    def _status_poll_msg(self, source_name: str, new_freq: int):
        self.status_bar.showMessage(
            f"Polling for '{source_name}' will change to {int(new_freq)}s after the current cycle.",
            4000
        )

    def on_stop(self):
        # stop all
        for sid in list(self.controllers.keys()):
            self._stop_source(sid)

        self.act_start.setEnabled(True)
        self.act_stop.setEnabled(False)

    def _update_plot_poll(self, sid: int, new_freq: int):
        ctrl = self.controllers.get(sid)
        if not ctrl:
            return
        try:
            ctrl.worker.freq_s = int(new_freq)
            # if you implemented the immediate realign flag in Worker:
            if hasattr(ctrl.worker, "_freq_changed"):
                ctrl.worker._freq_changed = True
            self.status_bar.showMessage(
                f"Polling set to {new_freq}s for '{(self.config.get('sources') or [])[sid].get('name', 'Source')}'.",
                4000)
        except Exception:
            pass

    def _stop_source(self, sid: int):
        ctrl = self.controllers.pop(sid, None)
        if ctrl:
            try:
                ctrl.stop()
            except Exception:
                pass
        plot = self.plots.pop(sid, None)
        if plot:
            try:
                plot.closed.disconnect()
            except Exception:
                pass
            plot.close()
        if not self.controllers:
            self.act_start.setEnabled(True)
            self.act_stop.setEnabled(False)

    def _on_point(self, sid, ts, count, is_anomaly, forecast):
        plot = self.plots.get(sid)
        if plot:
            plot.add_point(ts, count, is_anomaly, forecast)

    def on_error(self, msg: str):
        self.status_bar.showMessage(f"DB Error: {msg}", 10000)

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self, cfg=self.config.data)
        if not dlg.exec():
            return
        vals = dlg.get_values()
        self.config.save(vals)

        # Live update global polling to running controllers (per-source overrides still win)
        if self.controllers:
            for sid, ctrl in self.controllers.items():
                s_cfg = (self.config.get("sources") or [])[sid]
                if not s_cfg.get("polling_frequency"):
                    try:
                        ctrl.worker.freq_s = vals["polling_frequency"]
                    except Exception:
                        pass
            self.status_bar.showMessage("Settings saved. Polling updated now; model params & client path apply on new connections.", 7000)

    def _show_about(self):
        about = QMessageBox(self)
        about.setWindowTitle("About Oracle Queue Monitor")

        # Try loading logo from resources
        res_path = Path(__file__).resolve().parent.parent / "resources"
        logo_path = res_path / "app.png"  # or "logo.png" if you add one
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaledToHeight(64)
            about.setIconPixmap(pixmap)
        else:
            about.setIcon(QMessageBox.Icon.Information)

        # Professional text with some formatting
        about.setText(
            f"<b>Oracle Queue Monitor v{__version__}</b><br><br>"
            "Monitor multiple Oracle DB queues with live charts and "
            "adaptive one-sided anomaly detection.<br><br>"
            "Built with <b>PyQt6</b> and <b>pyqtgraph</b>.<br><br>"
            "<small>© 2025 Nektarios Christou<br>"
            "<a href='mailto:nekcht@gmail.com'>nekcht@gmail.com</a></small>"
        )
        about.setTextFormat(Qt.TextFormat.RichText)  # enable HTML formatting
        about.setStandardButtons(QMessageBox.StandardButton.Ok)

        about.exec()

    def closeEvent(self, e):
        try:
            self.on_stop()
        finally:
            super().closeEvent(e)
