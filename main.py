from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
import sys
from core.logger import logger
from core import __version__


def main():
    logger.info(f"Launching GUI v{__version__}")
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
