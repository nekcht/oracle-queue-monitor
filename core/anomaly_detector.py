# core/anomaly_detector.py
import numpy as np
from collections import deque
from statsmodels.tsa.ar_model import AutoReg
import warnings
from core.logger import logger

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

    Forecasts next value via AutoReg; falls back to robust linear trend.
    Flags upward anomalies only (drops ignored).
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

        logger.info(
            f"AnomalyDetector initialized | "
            f"window_size={self.window_size}, k_upper={self.k_upper}, "
            f"min_rel_increase={self.min_rel_increase}, q={self.q}, "
            f"ew_alpha={self.ew_alpha}, debounce={self.debounce}"
        )

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

        if n < max(8, self.window_size // 4):
            logger.debug(f"AD warm-up | n={n}, val={v}")
            return False, None

        data = np.asarray(self.buffer, dtype=float)
        hist = data[:-1]

        # Forecast next value
        try:
            lags = min(8, max(1, n // 5))
            res = AutoReg(hist, lags=lags, old_names=False).fit()
            forecast = float(res.predict(start=len(hist), end=len(hist))[0])
            base_scale = (
                float(np.std(res.resid))
                if getattr(res, "resid", None) is not None and len(res.resid) > 1
                else _mad_std(hist)
            )
            logger.debug(f"AD forecast | val={v} fc={forecast:.3f} lags={lags} base_std={base_scale:.3f}")
        except Exception as e:
            x = np.arange(len(hist))
            slope, intercept = np.polyfit(x, hist, 1)
            forecast = float(slope * len(hist) + intercept)
            base_scale = _mad_std(hist)
            logger.warning(f"AD fallback forecast used | val={v} fc={forecast:.3f} err={e}")

        forecast = max(0.0, forecast)  # queues cannot be negative

        resid = v - forecast
        resid_up = max(0.0, resid)

        # EWMA scale update
        self._ew_update(abs(resid))
        ew_std = float(np.sqrt(max(self._ew_var, 1e-12)))

        # Empirical quantile threshold
        if resid_up > 0:
            self.res_up_hist.append(resid_up)

        thr_quant = 0.0
        if len(self.res_up_hist) >= max(10, self.window_size // 6):
            thr_quant = float(np.quantile(np.asarray(self.res_up_hist, dtype=float), self.q))

        thr_stat = self.k_upper * max(ew_std, 1e-6)
        thr_rel = self.min_rel_increase * max(forecast, 1.0)
        threshold = max(thr_stat, thr_rel, thr_quant)

        is_anom = resid_up > threshold

        if self._cooldown > 0:
            is_anom = False
            self._cooldown -= 1
        elif is_anom:
            self._cooldown = self.debounce
            logger.warning(
                f"Anomaly triggered | val={v} fc={forecast:.3f} resid_up={resid_up:.3f} "
                f"thr={threshold:.3f} (stat={thr_stat:.3f}, rel={thr_rel:.3f}, q={thr_quant:.3f})"
            )
        else:
            logger.debug(
                f"AD eval | val={v} fc={forecast:.3f} resid_up={resid_up:.3f} "
                f"thr={threshold:.3f} -> anom={is_anom}"
            )

        return bool(is_anom), float(forecast)
