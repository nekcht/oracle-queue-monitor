# Oracle Queue Monitor

**Multi-source Oracle DB queue monitor with real-time plotting and one-sided (upward) anomaly detection (PyQt6 + pyqtgraph).**

## Features
- Monitor multiple Oracle DB sources simultaneously
- Custom SQL queries per source (e.g., `SELECT COUNT(*) FROM …`)
- Real-time plotting with PyQt6 + pyqtgraph
- One-sided anomaly detection (flags only upward spikes)
- Per-source polling frequency (configurable at runtime)
- Configurable via `settings.json`
- GUI for managing sources and settings

## Screenshots
*(Add screenshots here once you take them!)*

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
```

## Oracle Instant Client
- If your database supports **Oracle Thin mode** (newer versions), no client installation is required.  
- For **older Oracle versions** you will need the [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html).  
- Download it, extract it, and point to its folder in your `settings.json` under the key:
  ```json
  "instant_client_path": "C:\\path\\to\\your\\instantclient_xx_x"


## Settings
The `settings.json` file stores global settings (like `instant_client_path`) and your list of DB sources.  
Each source entry contains connection details, query, and polling frequency.

Example:
```json
{
  "window_size": 64,
  "k_upper": 3.0,
  "min_rel_increase": 0.25,
  "q": 0.995,
  "ew_alpha": 0.2,
  "debounce": 1,
  "instant_client_path": "C:\\oracle\\instantclient_23_9",
  "sources": [
    {
      "name": "DEMO",
      "host": "demo"
      "port": "demo",
      "service_name": "demo",
      "user": "demo",
      "password": "demo",
      "query": "SELECT COUNT(*) FROM A",
      "polling_frequency": 5
    }
  ]
}
```

## License
MIT — see [LICENSE](LICENSE).
