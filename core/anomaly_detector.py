import numpy as np
from collections import deque
from statsmodels.tsa.ar_model import AutoReg
import warnings
from core.logger import logger

warnings.filterwarnings('ignore')

class AnomalyDetector:
    def __init__(self, window_size=20, k=3.0):
        self.window_size = int(window_size)
        self.k = float(k)
        self.buffer = deque(maxlen=self.window_size)
        logger.info(f"AnomalyDetector initialized | window_size={self.window_size} k={self.k}")

    def add_and_predict(self, value):
        self.buffer.append(float(value))
        forecast = None
        is_anom = False
        try:
            data = np.array(self.buffer)
            if len(data) < max(3, self.window_size // 4):
                logger.debug(f"AD skip fit | n={len(data)} need>={max(3, self.window_size // 4)} value={value}")
                return False, None
            model = AutoReg(data[:-1], lags=min(5, max(1, len(data)//4)), old_names=False)
            res = model.fit()
            pred = res.predict(start=len(data)-1, end=len(data)-1)[0]
            forecast = float(pred)
            resid = abs(self.buffer[-1] - forecast)
            std = np.std(res.resid) if hasattr(res, 'resid') and len(res.resid)>0 else np.std(data)
            std = std or 1e-6
            is_anom = resid > (self.k * std)
            logger.debug(f"AD eval | val={value} fc={forecast:.3f} resid={resid:.3f} std={std:.3f} k={self.k} anom={is_anom}")
        except Exception as e:
            logger.exception(f"AD fallback due to error: {e}")
            try:
                xs = np.arange(len(self.buffer))
                coef = np.polyfit(xs, np.array(self.buffer), 1)
                forecast = float(np.polyval(coef, len(self.buffer)))
                slope = coef[0]
                is_anom = slope > 0 and self.buffer[-1] > np.mean(self.buffer)*1.5
                logger.debug(f"AD fallback | slope={slope:.6f} fc={forecast:.3f} anom={is_anom}")
            except Exception:
                logger.exception("AD fallback failed")
        return is_anom, forecast
