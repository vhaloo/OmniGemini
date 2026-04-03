import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "gemini_cli_path": "gemini",
    "camera_index": 0,
    "ducking_enabled": True,
    "loudness_threshold": 8000
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(data)
            return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
