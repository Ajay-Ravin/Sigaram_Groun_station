"""
Serial Reader Thread — QThread that reads from a serial port,
parses telemetry, emits signals for GUI updates, and logs to CSV.
"""
import time
import serial
from PyQt6.QtCore import QThread, pyqtSignal

from backend.telemetry_parser import (
    parse_rocket_line,
    parse_cansat_line,
    rocket_packet_to_gui,
    cansat_packet_to_gui,
)
from backend.csv_logger import get_logger


class SerialReaderThread(QThread):
    """
    Reads CSV telemetry from a serial port in a background thread.
    Emits Qt signals so the GUI can update safely from the main thread.
    """

    # Signals for passing data to the main GUI thread
    rocket_data_received = pyqtSignal(dict)
    cansat_data_received = pyqtSignal(dict)
    log_message = pyqtSignal(str)
    connection_error = pyqtSignal(str)

    def __init__(self, port, baudrate=115200, source_type="ROCKET"):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.source_type = source_type.upper()
        self._is_running = True
        self.serial_conn = None

        # State for velocity computation
        self._prev_altitude = 0.0
        self._prev_time = time.time()

    def run(self):
        self.log_message.emit(
            f"[SYS] Connecting to {self.port} at {self.baudrate} baud..."
        )
        try:
            self.serial_conn = serial.Serial(
                self.port, self.baudrate, timeout=1.0
            )
            self.log_message.emit(f"[SYS] Connected to {self.port}")
        except Exception as e:
            self.connection_error.emit(
                f"[ERR] Failed to connect to {self.port}: {e}"
            )
            return

        logger = get_logger()

        while self._is_running:
            try:
                if self.serial_conn.in_waiting > 0:
                    raw = self.serial_conn.readline()
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue

                    # Show raw CSV line in the terminal
                    self.log_message.emit(line)

                    # Parse and emit
                    now = time.time()
                    dt = now - self._prev_time
                    self._prev_time = now

                    if self.source_type == "ROCKET":
                        pkt = parse_rocket_line(line)
                        if pkt:
                            gui_dict = rocket_packet_to_gui(
                                pkt, self._prev_altitude, dt
                            )
                            self._prev_altitude = pkt.altitude
                            self.rocket_data_received.emit(gui_dict)
                        logger.log_rocket(line)
                    else:
                        pkt = parse_cansat_line(line)
                        if pkt:
                            gui_dict = cansat_packet_to_gui(
                                pkt, self._prev_altitude, dt
                            )
                            self._prev_altitude = pkt.altitude
                            self.cansat_data_received.emit(gui_dict)
                        logger.log_cansat(line)

            except serial.SerialException as e:
                self.connection_error.emit(
                    f"[ERR] Serial error on {self.port}: {e}"
                )
                break
            except Exception as e:
                self.log_message.emit(f"[ERR] Data processing error: {e}")

            time.sleep(0.005)

        # Cleanup
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.log_message.emit(f"[SYS] Disconnected from {self.port}")

    def send_command(self, command: str) -> bool:
        """Send a command string over the serial connection (thread-safe for writes)."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write((command + "\n").encode("utf-8"))
                return True
            except Exception:
                return False
        return False

    def stop(self):
        self._is_running = False
        self.wait()
