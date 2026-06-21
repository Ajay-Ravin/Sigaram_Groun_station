"""
Backend Configuration — Loads from backend_config.json
"""
import os
import json


class Config:
    ROCKET_PORT = "COM3"
    ROCKET_BAUD = 115200
    CANSAT_PORT = "COM4"
    CANSAT_BAUD = 115200
    LOG_DIR = "logs"

    @classmethod
    def load_from_file(cls):
        """Load configuration from backend_config.json if it exists."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "backend_config.json",
        )
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                cls.ROCKET_PORT = data.get("rocket_port", cls.ROCKET_PORT)
                cls.ROCKET_BAUD = data.get("rocket_baud", cls.ROCKET_BAUD)
                cls.CANSAT_PORT = data.get("cansat_port", cls.CANSAT_PORT)
                cls.CANSAT_BAUD = data.get("cansat_baud", cls.CANSAT_BAUD)
            except Exception:
                pass


# Auto-load on import
Config.load_from_file()
