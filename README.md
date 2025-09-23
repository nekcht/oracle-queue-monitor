# Oracle Queue Monitor

A simple tool to monitor Oracle database queues with live charts and basic anomaly detection.  
Built with PyQt6 and pyqtgraph.
  
## Case Flow
1. Define one or more database sources (connection info + query).
2. Each source runs your custom query that returns a single numeric value (e.g., `SELECT COUNT(*) ...`).
3. Values are collected at the chosen polling interval.
4. Results are shown in live plots, one window per source.
5. An anomaly is flagged if the queue grows unusually fast (upward-only detection).

## Screenshots

<table>
  <tr>
    <td align="center">
      <img src="docs/main_window.jpg" alt="Main Window" width="400"/><br/>
      <sub>Main Window</sub>
    </td>
    <td align="center">
      <img src="docs/plot.png" alt="Live Plot" width="400"/><br/>
      <sub>Live Plot</sub>
    </td>
  </tr>
</table>

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
The tool uses a rolling **AutoRegressive (AR)** model from [statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.tsa.ar_model.AutoReg.html) to forecast expected queue values.  
Only upward spikes are considered anomalies.  

## License
MIT - see [LICENSE](LICENSE).
