# core/config_manager.py
import json
from json import JSONDecodeError
from pathlib import Path

class AppConfig:
    def __init__(self, config_path="settings.json"):
        self.config_path = Path(config_path)
        # defaults
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
        print("Looking for config at:", self.config_path.resolve())

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except JSONDecodeError as e:
                print(f"Warning: settings.json is not valid JSON ({e}). Using defaults.")
            except UnicodeDecodeError as e:
                print(f"Warning: settings.json encoding error ({e}). "
                      f"Re-save the file as UTF-8. Using defaults.")
            except Exception as e:
                print(f"Warning: failed to read settings.json ({e}). Using defaults.")

        # ---- Ensure 'sources' key exists
        self.data.setdefault("sources", [])

        # ── hoist first per-source instant_client_path to global if global empty
        if not self.data.get("instant_client_path"):
            for src in self.data["sources"]:
                icp = src.pop("instant_client_path", "")
                if icp:
                    self.data["instant_client_path"] = icp
                    break
        else:
            # drop any leftover per-source instant_client_path
            for src in self.data["sources"]:
                src.pop("instant_client_path", None)

        # existing query migration stays the same...
        for src in self.data.get("sources", []):
            if not src.get("query"):
                table = src.get("table_name", "")
                col = src.get("column_name", "")
                if table:
                    src["query"] = f"SELECT COUNT({col}) FROM {table}" if col else f"SELECT COUNT(*) FROM {table}"
            src.pop("table_name", None)
            src.pop("column_name", None)

        # --- Backward compat: if old anomaly_k exists, map to k_upper once
        if "anomaly_k" in self.data and "k_upper" not in self.data:
            try:
                self.data["k_upper"] = float(self.data.get("anomaly_k", 3.0))
            except Exception:
                pass
            self.data.pop("anomaly_k", None)

        # Ensure all new keys exist
        self.data.setdefault("k_upper", 3.0)
        self.data.setdefault("min_rel_increase", 0.25)
        self.data.setdefault("q", 0.995)
        self.data.setdefault("ew_alpha", 0.2)
        self.data.setdefault("debounce", 1)

    def save(self, new_data=None):
        if new_data:
            self.data.update(new_data)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)  # keep Greek readable
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
