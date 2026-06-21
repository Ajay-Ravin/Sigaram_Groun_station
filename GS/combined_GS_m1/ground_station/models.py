"""
Telemetry Data Models — Enums, Dataclasses, Interface
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal


class RocketState(Enum):
    BOOT = "Boot"
    PRE_LAUNCH = "Pre_launch"
    ASCENT = "ascent"
    DEPLOYMENT = "Deployment"
    DESCENT = "Descent"
    IMPACT_RECOVERY = "Impact/recovery"


class CanSatState(Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    DEPLOY = "DEPLOY"
    FALL = "FALL"
    LAND = "LAND"
    POST = "POST"


@dataclass
class RocketTelemetry:
    altitude: float = 0.0
    velocity: float = 0.0
    acceleration: float = 0.0
    temperature: float = 25.0
    pressure: float = 101300.0  # Pa
    latitude: float = 0.0
    longitude: float = 0.0
    gps_fix: str = "3D - 8 satellites"
    battery: int = 87
    signal: int = -62
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    state: RocketState = RocketState.BOOT


@dataclass
class CanSatTelemetry:
    altitude: float = 0.0
    velocity: float = 0.0
    pressure: float = 101300.0  # Pa
    temperature: float = 25.0
    latitude: float = 0.0
    longitude: float = 0.0
    satellite_count: int = 8
    fix_type: str = "3D"
    battery: int = 74
    signal: int = -71
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    state: CanSatState = CanSatState.IDLE


@dataclass
class MissionEvent:
    time: float = 0.0
    label: str = ""
    color: str = "#00FF88"


class TelemetryDataInterface(QObject):
    """Central interface for telemetry data flow"""

    rocket_updated = pyqtSignal(object)
    cansat_updated = pyqtSignal(object)
    event_logged = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.rocket = RocketTelemetry()
        self.cansat = CanSatTelemetry()
        self.elapsed_time: float = 0
        self.rocket_history: List[RocketTelemetry] = []
        self.cansat_history: List[CanSatTelemetry] = []
        self.events: List[MissionEvent] = []
        self._last_rocket_state = RocketState.BOOT
        self._last_cansat_state = CanSatState.IDLE

    # --- state-change event labels ---
    _ROCKET_EVENTS = {
        RocketState.BOOT: ("SYSTEM BOOT", "#6088AA"),
        RocketState.PRE_LAUNCH: ("PRE-LAUNCH READY", "#FFB800"),
        RocketState.ASCENT: ("ASCENT PHASE", "#FF3344"),
        RocketState.DEPLOYMENT: ("DEPLOYMENT DETECTED", "#00FF88"),
        RocketState.DESCENT: ("DESCENT PHASE", "#3388FF"),
        RocketState.IMPACT_RECOVERY: ("IMPACT / RECOVERY ACTIVE", "#00FF88"),
    }
    _CANSAT_EVENTS = {
        CanSatState.ARMED: ("CANSAT ARMED", "#FFB800"),
        CanSatState.DEPLOY: ("CANSAT DEPLOYED", "#00FF88"),
        CanSatState.FALL: ("PARACHUTE DESCENT", "#00D4FF"),
        CanSatState.LAND: ("LANDING DETECTED", "#00FF88"),
        CanSatState.POST: ("POST-LANDING", "#6088AA"),
    }

    def update_rocket(self, t: RocketTelemetry):
        self.rocket = t
        self.rocket_history.append(RocketTelemetry(**vars(t)))
        if len(self.rocket_history) > 6000:
            self.rocket_history.pop(0)
        # auto-log state changes
        if t.state != self._last_rocket_state and t.state in self._ROCKET_EVENTS:
            label, color = self._ROCKET_EVENTS[t.state]
            self._log(label, color)
        self._last_rocket_state = t.state
        self.rocket_updated.emit(t)

    def update_cansat(self, t: CanSatTelemetry):
        self.cansat = t
        self.cansat_history.append(CanSatTelemetry(**vars(t)))
        if len(self.cansat_history) > 6000:
            self.cansat_history.pop(0)
        if t.state != self._last_cansat_state and t.state in self._CANSAT_EVENTS:
            label, color = self._CANSAT_EVENTS[t.state]
            self._log(label, color)
        self._last_cansat_state = t.state
        self.cansat_updated.emit(t)

    def update_elapsed(self, s: float):
        self.elapsed_time = s

    def _log(self, label: str, color: str):
        ev = MissionEvent(time=self.elapsed_time, label=label, color=color)
        self.events.insert(0, ev)
        if len(self.events) > 100:
            self.events.pop()
        self.event_logged.emit(ev)
