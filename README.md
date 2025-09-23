# Oracle Queue Monitor

A simple tool to monitor Oracle database queues with live charts and basic anomaly detection.  
Built with PyQt6 and pyqtgraph.

## Case Flow
1. Define one or more database sources (connection info + query).
2. Each source runs a query that returns a single numeric value (e.g., `SELECT COUNT(*) ...`).
3. Values are collected at the chosen polling interval.
4. Results are shown in live plots, one window per source.
5. An anomaly is flagged if the queue grows unusually fast (upward-only detection).

## Screenshots
*(Add screenshots here once you take them!)*

## Quickstart
```bash
git clone https://github.com/nekcht/oracle-queue-monitor.git
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
- Newer Oracle versions: works without client (Thin mode).  
- Older versions: download [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html) and set its folder in `settings.json` or in the GUI (Settings).


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

## License
MIT — see [LICENSE](LICENSE).
