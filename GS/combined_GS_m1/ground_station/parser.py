"""
Ground Station Parser — Thin wrapper around the backend telemetry parser.
Kept for backward compatibility with any code that imports from here.
"""
from backend.telemetry_parser import (
    parse_rocket_line,
    parse_cansat_line,
    rocket_packet_to_gui,
    cansat_packet_to_gui,
)
from ground_station.models import RocketState, CanSatState


class CSVTelemetryParser:
    """
    Parses incoming CSV telemetry strings.
    Delegates to backend.telemetry_parser functions.
    """

    def parse_line(self, line: str, source_type: str = "ROCKET") -> dict | None:
        """
        Parse a CSV line and return a dict compatible with
        RocketTelemetry / CanSatTelemetry constructors.
        Returns None if the line cannot be parsed.
        """
        if source_type.upper() == "ROCKET":
            pkt = parse_rocket_line(line)
            if pkt:
                return rocket_packet_to_gui(pkt)
            return None
        else:
            pkt = parse_cansat_line(line)
            if pkt:
                return cansat_packet_to_gui(pkt)
            return None
