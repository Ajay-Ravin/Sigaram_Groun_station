"""
Backend entry point — start_backend / stop_backend.
Populates GUI port dropdowns. Does NOT auto-connect or auto-simulate.
"""
from backend.serial_manager import get_available_ports
from backend.config import Config


def start_backend(window=None):
    """
    Initialize the backend:
    - Load configuration
    - Populate COM port dropdowns with detected system ports
    - Does NOT start any connections automatically
    """
    Config.load_from_file()

    if window is None:
        return

    # Populate COM Monitor port dropdowns with real system ports
    if hasattr(window, "com_monitor_page"):
        ports = get_available_ports()
        page = window.com_monitor_page

        # Rocket port dropdown
        page.r_port.clear()
        page.r_port.addItems(ports)
        idx = page.r_port.findText(Config.ROCKET_PORT)
        if idx >= 0:
            page.r_port.setCurrentIndex(idx)

        # CanSat port dropdown
        page.c_port.clear()
        page.c_port.addItems(ports)
        idx = page.c_port.findText(Config.CANSAT_PORT)
        if idx >= 0:
            page.c_port.setCurrentIndex(idx)


def stop_backend():
    """Clean up backend resources. Serial threads are managed by the GUI."""
    pass
