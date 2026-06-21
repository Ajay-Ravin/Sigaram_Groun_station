"""
Telemetry Packet Models — Dataclasses matching real CSV packet formats.

Rocket: 17 fields
CanSat: 14 fields
"""
from dataclasses import dataclass


@dataclass
class RocketPacket:
    """Matches the 17-field CSV format from the rocket avionics."""
    team_id: str = ""
    mission_time: float = 0.0
    packet_count: int = 0
    altitude: float = 0.0
    pressure: float = 101325.0
    temperature: float = 25.0
    battery_voltage: float = 0.0
    gnss_latitude: float = 0.0
    gnss_longitude: float = 0.0
    gnss_altitude: float = 0.0
    gnss_satellites: int = 0
    acceleration: float = 0.0
    gyro_angular_rate: float = 0.0
    flight_state: str = "Boot"
    primary_altimeter_status: str = "OK"
    redundant_altimeter_status: str = "OK"
    failure_counter: int = 0


@dataclass
class CanSatPacket:
    """Matches the 14-field CSV format from the CanSat payload."""
    team_id: str = ""
    mission_time: float = 0.0
    packet_count: int = 0
    altitude: float = 0.0
    pressure: float = 101325.0
    temperature: float = 25.0
    battery_voltage: float = 0.0
    gnss_latitude: float = 0.0
    gnss_longitude: float = 0.0
    gnss_altitude: float = 0.0
    gnss_satellites: int = 0
    acceleration: float = 0.0
    gyro_angular_rate: float = 0.0
    flight_state: str = "IDLE"
