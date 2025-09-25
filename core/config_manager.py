import json
from pathlib import Path
from core.logger import logger

def _mask(d: dict) -> dict:
    m = dict(d)
    for k in list(m.keys()):
        if k.lower() in ("password",):
            m[k] = "***"
    return m

class AppConfig:
    def __init__(self, config_path="settings.json"):
        self.config_path = Path(config_path)
        self.data = {
            "window_size": 64,
            "k_upper": 3.0,
            "min_rel_increase": 0.25,
            "q": 0.995,
            "ew_alpha": 0.2,
            "debounce": 1,
            "instant_client_path": r"C:\oracle\instantclient_23_9",
            "sources": []
        }
        self.load()
        logger.info(f"Config loaded from {self.config_path.resolve()}")

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding="utf-8") as f:
                    incoming = json.load(f)
                    self.data.update(incoming)
                logger.info(f"Config read OK | {self.config_path} | { _mask(self.data) }")
            except Exception as e:
                logger.exception(f"Failed to read {self.config_path}: {e}")
        if "sources" not in self.data:
            self.data["sources"] = []
            logger.info("Config migration: added empty 'sources'")

    def save(self, new_data=None):
        if new_data:
            self.data.update(new_data)
        try:
            with open(self.config_path, 'w', encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            logger.info(f"Config saved | {self.config_path} | { _mask(self.data) }")
        except Exception as e:
            logger.exception(f"Error saving settings: {e}")

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        logger.debug(f"Config set | {key}={value if key.lower()!='password' else '***'}")
