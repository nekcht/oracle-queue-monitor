# Oracle Queue Monitor

A simple tool to monitor Oracle database queues with live charts and basic anomaly detection.  
  
## How it works
- Add one or more sources with connection info and a query.  
- Each query must return a single number (e.g. `SELECT COUNT(*) ...`).  
- Values are fetched at the polling interval and shown in live plots.  
- Each source opens its own window.  
- An alert is raised if the queue spikes.  

Older Oracle versions need the [Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html). Set its path in `settings.json` or from the GUI under Settings.  

Anomalies are detected with an [AutoRegressive (AR)](https://www.statsmodels.org/stable/generated/statsmodels.tsa.ar_model.AutoReg.html) model. Only upward spikes are considered. 

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
