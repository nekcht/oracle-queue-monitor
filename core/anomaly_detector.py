# core/anomaly_detector.py
import numpy as np
from collections import deque
from statsmodels.tsa.ar_model import AutoReg
import warnings

warnings.filterwarnings("ignore")


def _mad_std(x: np.ndarray) -> float:
    """Robust std via MAD. Falls back to tiny epsilon."""
    if x.size == 0:
        return 1e-6
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    return max(1e-6, 1.4826 * mad)


class AnomalyDetector:
    """
    One-sided, adaptive spike detector for queue-like signals.

    - Forecasts next value via AutoReg; falls back to robust linear trend.
    - Computes upward residual r_up = max(0, y_t - forecast_t).
    - Maintains EWMA variance of residual magnitude for scale.
    - Keeps an empirical history of positive residuals; uses high quantile as threshold.
    - Flags anomaly if r_up exceeds the max of:
        k_upper * ew_std,
        min_rel_increase * max(forecast, 1),
        quantile_q(residual_up_history)

    Parameters
    ----------
    window_size : int
        Points kept for forecasting and empirical quantile.
    k_upper : float
        Multiplier for EW residual std (z-like one-sided threshold).
    min_rel_increase : float
        Minimum relative increase wrt forecast (e.g., 0.25 == +25%).
    q : float
        Empirical quantile (e.g., 0.995) over positive residuals.
    ew_alpha : float
        EWMA smoothing factor for residual magnitude (0<α<1).
    debounce : int
        Suppress the next N ticks after a trigger.
    """

    def __init__(
        self,
        window_size: int = 64,
        k_upper: float = 3.0,
        min_rel_increase: float = 0.25,
        q: float = 0.995,
        ew_alpha: float = 0.2,
        debounce: int = 1,
    ):
        self.window_size = max(16, int(window_size))
        self.k_upper = float(k_upper)
        self.min_rel_increase = float(min_rel_increase)
        self.q = float(q)
        self.ew_alpha = float(ew_alpha)
        self.debounce = max(0, int(debounce))

        self.buffer = deque(maxlen=self.window_size)  # raw values
        self.res_up_hist = deque(maxlen=self.window_size)  # positive residuals
        self._ew_mean = None  # EW mean of |residual|
        self._ew_var = None  # EW variance of |residual|
        self._cooldown = 0

    # internal: EWMA update on absolute residuals
    def _ew_update(self, x: float) -> None:
        a = self.ew_alpha
        if self._ew_mean is None:
            self._ew_mean = x
            self._ew_var = 1e-6
            return
        delta = x - self._ew_mean
        self._ew_mean += a * delta
        # Joseph stabilized variance update
        self._ew_var = (1 - a) * (self._ew_var + a * delta * delta)

    def add_and_predict(self, value):
        """
        Add new observation and return (is_anomaly, forecast).

        Returns
        -------
        is_anomaly : bool
            True only for upward spikes beyond adaptive thresholds.
        forecast : float or None
            Forecasted next value (None during warm-up).
        """
        v = float(value)
        self.buffer.append(v)
        n = len(self.buffer)

        # Warm-up: need a minimum history
        if n < max(8, self.window_size // 4):
            return False, None

        data = np.asarray(self.buffer, dtype=float)
        hist = data[:-1]

        # Forecast next value
        try:
            lags = min(8, max(1, n // 5))
            res = AutoReg(hist, lags=lags, old_names=False).fit()
            forecast = float(res.predict(start=len(hist), end=len(hist))[0])
            base_scale = float(np.std(res.resid)) if getattr(res, "resid", None) is not None and len(res.resid) > 1 else _mad_std(hist)
        except Exception:
            x = np.arange(len(hist))
            slope, intercept = np.polyfit(x, hist, 1)
            forecast = float(slope * len(hist) + intercept)
            base_scale = _mad_std(hist)

        # Queues cannot be negative
        forecast = max(0.0, forecast)

        # Residuals and adaptive scales
        resid = v - forecast
        resid_up = max(0.0, resid)

        # EWMA scale on absolute residuals
        self._ew_update(abs(resid))
        ew_std = float(np.sqrt(max(self._ew_var, 1e-12)))

        # Empirical quantile over positive residuals
        if resid_up > 0:
            self.res_up_hist.append(resid_up)

        thr_quant = 0.0
        if len(self.res_up_hist) >= max(10, self.window_size // 6):
            thr_quant = float(np.quantile(np.asarray(self.res_up_hist, dtype=float), self.q))

        # Compose final one-sided threshold (generic, no hard caps)
        thr_stat = self.k_upper * max(ew_std, 1e-6)
        thr_rel = self.min_rel_increase * max(forecast, 1.0)
        threshold = max(thr_stat, thr_rel, thr_quant, base_scale * 0.0)  # base_scale only computed; not directly used

        is_anom = resid_up > threshold

        # Debounce consecutive triggers
        if self._cooldown > 0:
            is_anom = False
            self._cooldown -= 1
        elif is_anom:
            self._cooldown = self.debounce

        return bool(is_anom), float(forecast)
