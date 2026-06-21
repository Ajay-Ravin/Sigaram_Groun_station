#!/usr/bin/env python3
"""
Launch Ground Station UI with simulated telemetry data for testing.
Runs backend processing pipelines and links them to the PyQt GUI.
"""
import sys
import os

# PyQt6 automatically handles plugin path mapping inside a virtual environment.

if sys.platform == "darwin":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_plugins = os.path.abspath(os.path.join(base_dir, "..", "..", ".venv", "lib", "python3.13", "site-packages", "PyQt6", "Qt6", "plugins"))
    if os.path.exists(venv_plugins):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = venv_plugins


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ground_station.app import GroundStationApp
from backend import start_backend, stop_backend

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Ground Station — Production Backend")

    window = GroundStationApp()
    
    # Start the backend and link it to the UI
    start_backend(window)

    window.show()
    window.activateWindow()
    window.raise_()

    try:
        sys.exit(app.exec())
    finally:
        stop_backend()

if __name__ == "__main__":
    main()
