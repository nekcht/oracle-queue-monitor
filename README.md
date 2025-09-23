# Oracle Queue Monitor

**Multi-source Oracle DB queue monitor with real-time plotting and one-sided (upward) anomaly detection (PyQt6 + pyqtgraph).**

## Features
- Monitor multiple Oracle DB sources simultaneously
- Custom SQL queries per source (e.g., `SELECT COUNT(*) FROM …`)
- Real-time plotting with PyQt6 + pyqtgraph
- One-sided anomaly detection (flags only upward spikes)
- Per-source polling frequency
- Configurable via `settings.json`
- GUI for managing sources and settings

## Screenshots
...

## Quickstart
```bash
git clone https://github.com/<your-username>/oracle-queue-monitor.git
cd oracle-queue-monitor

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp settings.example.json settings.json  # edit with your DB info
python main.py
