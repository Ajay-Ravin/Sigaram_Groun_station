"""
Serial Manager — Cross-platform port detection and command helper.
"""
import serial.tools.list_ports


def get_available_ports() -> list[str]:
    """
    Detect real serial ports on the system.
    Returns a list with 'Simulator' as the first option,
    followed by all detected system ports.
    Works on macOS (/dev/cu.*), Windows (COM*), and Linux (/dev/ttyUSB*).
    """
    ports = [p.device for p in serial.tools.list_ports.comports()]
    result = ["Simulator"]
    result.extend(sorted(ports))
    return result


def send_serial_command(serial_conn, command: str) -> bool:
    """
    Send a command string over an open serial connection.
    Returns True on success, False on failure.
    """
    if serial_conn and serial_conn.is_open:
        try:
            serial_conn.write((command + "\n").encode("utf-8"))
            return True
        except Exception:
            return False
    return False
