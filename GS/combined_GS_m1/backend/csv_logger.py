"""
CSV Logger — Writes telemetry to timestamped CSV files.
"""
import os
from datetime import datetime
from backend.config import Config


class CSVLogger:
    """Creates and appends to daily CSV log files for Rocket and CanSat."""

    def __init__(self):
        self.log_dir = Config.LOG_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")

        self.rocket_file = os.path.join(self.log_dir, f"Rocket_{date_str}.csv")
        self.cansat_file = os.path.join(self.log_dir, f"CanSat_{date_str}.csv")

        self._init_file(
            self.rocket_file,
            "TEAM_ID,MISSION_TIME,PACKET_COUNT,ALTITUDE,PRESSURE,TEMPERATURE,"
            "BATTERY_VOLTAGE,GNSS_LATITUDE,GNSS_LONGITUDE,GNSS_ALTITUDE,"
            "GNSS_SATELLITES,ACCELERATION,GYRO_ANGULAR_RATE,FLIGHT_STATE,"
            "PRIMARY_ALTIMETER_STATUS,REDUNDANT_ALTIMETER_STATUS,FAILURE_COUNTER",
        )
        self._init_file(
            self.cansat_file,
            "TEAM_ID,MISSION_TIME,PACKET_COUNT,ALTITUDE,PRESSURE,TEMPERATURE,"
            "BATTERY_VOLTAGE,GNSS_LATITUDE,GNSS_LONGITUDE,GNSS_ALTITUDE,"
            "GNSS_SATELLITES,ACCELERATION,GYRO_ANGULAR_RATE,FLIGHT_STATE",
        )

    @staticmethod
    def _init_file(filepath, header):
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                f.write(header + "\n")

    def log_rocket(self, line: str):
        """Append a raw rocket CSV line to the log file."""
        try:
            with open(self.rocket_file, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def log_cansat(self, line: str):
        """Append a raw CanSat CSV line to the log file."""
        try:
            with open(self.cansat_file, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass


# Lazy singleton
_instance = None


def get_logger() -> CSVLogger:
    global _instance
    if _instance is None:
        _instance = CSVLogger()
    return _instance
