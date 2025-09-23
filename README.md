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
python main.py
```

## Oracle Instant Client
- If your database supports **Oracle Thin mode** (newer versions), no client installation is required.  
- For **older Oracle versions** you will need the [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html).  
- Download it, extract it, and provide its folder path in one of two ways:
  1. In your `settings.json` under the key:
     ```json
     "instant_client_path": "C:\\path\\to\\your\\instantclient_xx_x"
     ```
     (replace the path and version with your actual installation).
  2. Or, set it directly from the **GUI → Settings** dialog (no need to edit JSON manually).

## Statistical Model
We use a rolling **AutoRegressive (AR)** forecast to predict the next queue value and detect **upward-only** anomalies (drops are ignored since queues can naturally go to 0).  
A point is flagged if the upward residual exceeds adaptive thresholds.

**Parameters**
- `window_size` — samples kept for forecasting/history. Larger = smoother, smaller = more reactive.
- `k_upper` — σ-multiplier on an EWMA-based residual scale (z-like threshold).
- `min_rel_increase` — minimum relative jump vs forecast (prevents tiny bumps from triggering).
- `q` — empirical quantile (e.g., 0.995) of past positive residuals, acting as a learned upper bound.
- `ew_alpha` — smoothing factor (0–1) for the residual EWMA scale (how fast it adapts).
- `debounce` — suppress triggers for N ticks after one fires (reduces alert spam on plateaus).

**Trigger rule (one-sided):**
```
residual_up = max(0, actual - forecast)

is_anomaly if residual_up >
    max( k_upper * ew_std,
         min_rel_increase * max(forecast, 1),
         quantile_q(positive_residual_history) )
```

## Settings
`settings.json` holds global settings and your sources. Each source has connection details, a SQL query that returns **exactly one numeric value**, and an optional per-source polling interval.

Example:
```json
{
  "window_size": 64,
  "k_upper": 3.0,
  "min_rel_increase": 0.25,
  "q": 0.995,
  "ew_alpha": 0.2,
  "debounce": 1,
  "instant_client_path": "C:\\path\\to\\your\\instantclient_xx_x",
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

## Requirements
- Python 3.10+
- Install: `pip install -r requirements.txt`  
  (PyQt6, pyqtgraph, numpy, statsmodels, oracledb)
