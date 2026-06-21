"""
Telemetry Parser — Converts raw CSV lines into packet dataclasses,
and maps packet fields to existing GUI model fields.
"""
from backend.telemetry_models import RocketPacket, CanSatPacket
from ground_station.models import RocketState, CanSatState


# ── State string → Enum maps ──────────────────────────────────
_ROCKET_STATE_MAP: dict[str, RocketState] = {}
for _s in RocketState:
    _ROCKET_STATE_MAP[_s.value.lower()] = _s
    _ROCKET_STATE_MAP[_s.name.lower()] = _s

_CANSAT_STATE_MAP: dict[str, CanSatState] = {}
for _s in CanSatState:
    _CANSAT_STATE_MAP[_s.value.lower()] = _s
    _CANSAT_STATE_MAP[_s.name.lower()] = _s


# ── Raw CSV → Packet dataclass ─────────────────────────────────

def parse_rocket_line(line: str) -> RocketPacket | None:
    """Parse a 17-field CSV rocket telemetry line into a RocketPacket."""
    line = line.strip()
    if not line:
        return None
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 17:
        return None
    try:
        return RocketPacket(
            team_id=parts[0],
            mission_time=float(parts[1]),
            packet_count=int(float(parts[2])),
            altitude=float(parts[3]),
            pressure=float(parts[4]),
            temperature=float(parts[5]),
            battery_voltage=float(parts[6]),
            gnss_latitude=float(parts[7]),
            gnss_longitude=float(parts[8]),
            gnss_altitude=float(parts[9]),
            gnss_satellites=int(float(parts[10])),
            acceleration=float(parts[11]),
            gyro_angular_rate=float(parts[12]),
            flight_state=parts[13].strip(),
            primary_altimeter_status=parts[14].strip(),
            redundant_altimeter_status=parts[15].strip(),
            failure_counter=int(float(parts[16])),
        )
    except (ValueError, IndexError):
        return None


def parse_cansat_line(line: str) -> CanSatPacket | None:
    """Parse a 14-field CSV CanSat telemetry line into a CanSatPacket."""
    line = line.strip()
    if not line:
        return None
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 14:
        return None
    try:
        return CanSatPacket(
            team_id=parts[0],
            mission_time=float(parts[1]),
            packet_count=int(float(parts[2])),
            altitude=float(parts[3]),
            pressure=float(parts[4]),
            temperature=float(parts[5]),
            battery_voltage=float(parts[6]),
            gnss_latitude=float(parts[7]),
            gnss_longitude=float(parts[8]),
            gnss_altitude=float(parts[9]),
            gnss_satellites=int(float(parts[10])),
            acceleration=float(parts[11]),
            gyro_angular_rate=float(parts[12]),
            flight_state=parts[13].strip(),
        )
    except (ValueError, IndexError):
        return None


# ── Packet → GUI-compatible dict ───────────────────────────────

def _voltage_to_percent(voltage: float) -> int:
    """Convert LiPo voltage (3.0V–4.2V) to 0–100 percent."""
    if voltage <= 0:
        return 0
    return max(0, min(100, int((voltage - 3.0) / 1.2 * 100)))


def rocket_packet_to_gui(
    pkt: RocketPacket,
    prev_altitude: float = 0.0,
    dt: float = 0.1,
) -> dict:
    """
    Convert a RocketPacket to a dict whose keys match
    ground_station.models.RocketTelemetry fields.
    Includes 'mission_time' (popped by the handler before constructing the dataclass).
    """
    velocity = (pkt.altitude - prev_altitude) / dt if dt > 0 else 0.0
    state = _ROCKET_STATE_MAP.get(pkt.flight_state.lower(), RocketState.BOOT)
    return {
        "altitude": pkt.altitude,
        "velocity": velocity,
        "acceleration": pkt.acceleration,
        "temperature": pkt.temperature,
        "pressure": pkt.pressure,
        "latitude": pkt.gnss_latitude,
        "longitude": pkt.gnss_longitude,
        "gps_fix": f"3D - {pkt.gnss_satellites} satellites",
        "battery": _voltage_to_percent(pkt.battery_voltage),
        "signal": -60,
        "roll": pkt.gyro_angular_rate,
        "pitch": 0.0,
        "yaw": 0.0,
        "state": state,
        "mission_time": pkt.mission_time,
    }


def cansat_packet_to_gui(
    pkt: CanSatPacket,
    prev_altitude: float = 0.0,
    dt: float = 0.1,
) -> dict:
    """
    Convert a CanSatPacket to a dict whose keys match
    ground_station.models.CanSatTelemetry fields.
    Includes 'mission_time' (popped by the handler before constructing the dataclass).
    """
    velocity = (pkt.altitude - prev_altitude) / dt if dt > 0 else 0.0
    state = _CANSAT_STATE_MAP.get(pkt.flight_state.lower(), CanSatState.IDLE)
    fix_type = "3D" if pkt.gnss_satellites >= 3 else "No Fix"
    return {
        "altitude": pkt.altitude,
        "velocity": velocity,
        "pressure": pkt.pressure,
        "temperature": pkt.temperature,
        "latitude": pkt.gnss_latitude,
        "longitude": pkt.gnss_longitude,
        "satellite_count": pkt.gnss_satellites,
        "fix_type": fix_type,
        "battery": _voltage_to_percent(pkt.battery_voltage),
        "signal": -60,
        "roll": pkt.gyro_angular_rate,
        "pitch": 0.0,
        "yaw": 0.0,
        "state": state,
        "mission_time": pkt.mission_time,
    }
