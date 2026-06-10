#!/usr/bin/env python3
"""
Launch Ground Station UI with simulated telemetry data for testing.
Run:  python3 run_with_sim.py
"""
import sys, os

if sys.platform == "darwin":
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = (
        "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13"
        "/site-packages/PyQt6/Qt6/plugins"
    )

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ground_station.app import GroundStationApp
from ground_station.models import (
    RocketTelemetry, CanSatTelemetry, RocketState, CanSatState,
)
from simulator.flight_sim import RocketSimulator, CanSatSimulator

_RS = {s.value: s for s in RocketState}
_CS = {s.value: s for s in CanSatState}


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Ground Station — SIM")

    window = GroundStationApp()
    window.show()
    window.activateWindow()
    window.raise_()

    rsim = RocketSimulator()
    csim = CanSatSimulator()
    elapsed = [0.0]

    def tick():
        dt = 0.1
        elapsed[0] += dt
        rd = rsim.step(dt)
        cd = csim.step(dt)

        window.receive_rocket_telemetry(RocketTelemetry(
            altitude=rd["altitude"], velocity=rd["velocity"],
            acceleration=rd["acceleration"], temperature=rd["temperature"],
            pressure=rd["pressure"], latitude=rd["latitude"],
            longitude=rd["longitude"], gps_fix=rd["gps_fix"],
            battery=rd["battery"], signal=rd["signal"],
            roll=rd["roll"], pitch=rd["pitch"], yaw=rd["yaw"],
            state=_RS.get(rd["state"], RocketState.PRE),
        ))
        window.receive_cansat_telemetry(CanSatTelemetry(
            altitude=cd["altitude"], velocity=cd["velocity"],
            pressure=cd["pressure"], temperature=cd["temperature"],
            latitude=cd["latitude"], longitude=cd["longitude"],
            satellite_count=cd["satellite_count"], fix_type=cd["fix_type"],
            battery=cd["battery"], signal=cd["signal"],
            roll=cd["roll"], pitch=cd["pitch"], yaw=cd["yaw"],
            state=_CS.get(cd["state"], CanSatState.IDLE),
        ))
        window.receive_elapsed_time(elapsed[0])

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(100)  # 10 Hz

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
