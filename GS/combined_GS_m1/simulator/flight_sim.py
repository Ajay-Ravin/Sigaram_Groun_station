#!/usr/bin/env python3
"""
Flight Simulator — Generates realistic rocket & CanSat telemetry
including gyroscope (roll/pitch/yaw) for testing the Ground Station UI.
"""
import math
import random


class RocketSimulator:
    """Simulates a sounding rocket flight profile with attitude."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.t = 0.0
        self.altitude = 0.0
        self.velocity = 0.0
        self.acceleration = 0.0
        self.temperature = 22.0
        self.pressure = 101325.0  # Pa
        self.phase = "Boot"
        self.max_alt = 0.0
        self.lat = 34.0522
        self.lon = -118.2437
        self.battery = 100
        self.signal = -55
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

        self.t_ign = 5.0
        self.t_burnout = 12.0
        self.t_apogee = 28.0
        self.t_land = 70.0
        self.thrust_accel = 85.0
        self.drag_coeff = 0.005

    def step(self, dt: float = 0.1) -> dict:
        self.t += dt
        n = random.gauss(0, 0.3)

        if self.t < 2.0:
            self.phase = "Boot"
            self.acceleration = self.velocity = self.altitude = 0
        elif self.t < self.t_ign:
            self.phase = "Pre_launch"
            self.acceleration = self.velocity = self.altitude = 0
        elif self.t < self.t_burnout:
            self.phase = "ascent"
            f = (self.t - self.t_ign) / (self.t_burnout - self.t_ign)
            self.acceleration = self.thrust_accel * (1 - 0.3 * f) - 9.81
            self.velocity += self.acceleration * dt
            self.altitude += self.velocity * dt
        elif self.t < self.t_apogee:
            self.phase = "ascent"
            drag = self.drag_coeff * self.velocity ** 2 * (1 if self.velocity > 0 else -1)
            self.acceleration = -9.81 - drag
            self.velocity += self.acceleration * dt
            self.altitude += self.velocity * dt
        elif self.t < self.t_apogee + 3.0:
            self.phase = "Deployment"
            self.velocity = max(-25.0, self.velocity - 5.0 * dt)
            self.altitude += self.velocity * dt
            self.acceleration = -2.0 + n
        else:
            self.phase = "Descent"
            self.velocity = max(-25.0, self.velocity - 5.0 * dt)
            self.altitude += self.velocity * dt
            self.acceleration = -2.0 + n
            if self.altitude <= 0:
                self.altitude = self.velocity = self.acceleration = 0
                self.phase = "Impact/recovery"

        self.max_alt = max(self.max_alt, self.altitude)
        self.altitude = max(0, self.altitude)
        self.temperature = 22.0 - 0.0065 * self.altitude + n * 0.5
        self.pressure = 101325.0 * (1 - 2.25577e-5 * self.altitude) ** 5.25588

        self.lat += random.gauss(0, 0.00001)
        self.lon += random.gauss(0, 0.00001)
        self.battery = max(0, 100 - self.t * 0.15)
        self.signal = -55 - self.altitude * 0.003 + random.gauss(0, 2)

        # Attitude simulation
        if self.phase == "ascent":
            if self.t < self.t_burnout:
                self.pitch = 85 + random.gauss(0, 2)
                self.roll += random.gauss(0, 0.5)
                self.yaw += random.gauss(0, 0.3)
            else:
                self.pitch = 85 - (self.t - self.t_burnout) * 3 + random.gauss(0, 1)
                self.roll += random.gauss(0, 1)
                self.yaw += random.gauss(0, 0.5)
        elif self.phase in ("Deployment", "Descent"):
            self.pitch *= 0.98
            self.roll *= 0.95
            self.yaw += random.gauss(0, 0.2)
        else:
            self.pitch = random.gauss(0, 0.3)
            self.roll = random.gauss(0, 0.3)
            self.yaw = random.gauss(0, 0.2)

        return {
            "altitude": round(self.altitude, 2),
            "velocity": round(self.velocity, 2),
            "acceleration": round(self.acceleration, 2),
            "temperature": round(self.temperature, 1),
            "pressure": round(self.pressure, 1),
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "gps_fix": f"3D - {random.randint(6, 12)} satellites",
            "battery": int(self.battery),
            "signal": int(self.signal),
            "roll": round(self.roll, 1),
            "pitch": round(self.pitch, 1),
            "yaw": round(self.yaw % 360, 1),
            "state": self.phase,
        }


class CanSatSimulator:
    """Simulates a CanSat deployment and descent with attitude."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.t = 0.0
        self.altitude = 0.0
        self.velocity = 0.0
        self.temperature = 22.0
        self.pressure = 101325.0
        self.phase = "IDLE"
        self.lat = 34.0525
        self.lon = -118.2440
        self.battery = 100
        self.signal = -60
        self.deploy_alt = 800.0
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.t_arm = 3.0
        self.t_deploy = 15.0
        self.t_land = 55.0

    def step(self, dt: float = 0.1) -> dict:
        self.t += dt
        n = random.gauss(0, 0.2)

        if self.t < self.t_arm:
            self.phase = "IDLE"
        elif self.t < self.t_deploy:
            self.phase = "ARMED"
            f = (self.t - self.t_arm) / (self.t_deploy - self.t_arm)
            self.altitude = self.deploy_alt * f
            self.velocity = self.deploy_alt / (self.t_deploy - self.t_arm)
        elif self.t < self.t_land:
            self.phase = "DEPLOY" if self.t < self.t_deploy + 2 else "FALL"
            f = (self.t - self.t_deploy) / (self.t_land - self.t_deploy)
            self.altitude = self.deploy_alt * (1 - f)
            self.velocity = -self.deploy_alt / (self.t_land - self.t_deploy) + n
        else:
            self.phase = "LAND" if self.t < self.t_land + 5 else "POST"
            self.altitude = self.velocity = 0

        self.altitude = max(0, self.altitude)
        self.temperature = 22.0 - 0.0065 * self.altitude + n
        self.pressure = 101325.0 * (1 - 2.25577e-5 * self.altitude) ** 5.25588

        self.lat += random.gauss(0, 0.00002)
        self.lon += random.gauss(0, 0.00002)
        self.battery = max(0, 100 - self.t * 0.2)
        self.signal = -60 - self.altitude * 0.005 + random.gauss(0, 2)

        # Attitude — slow spin under parachute
        if self.phase in ("DEPLOY", "FALL"):
            self.roll += random.gauss(0, 2)
            self.pitch = random.gauss(-5, 3)
            self.yaw += 1.5 + random.gauss(0, 0.5)
        elif self.phase in ("LAND", "POST"):
            self.roll *= 0.9
            self.pitch *= 0.9
            self.yaw += random.gauss(0, 0.1)
        else:
            self.roll = random.gauss(0, 0.5)
            self.pitch = random.gauss(0, 0.5)
            self.yaw = random.gauss(0, 0.3)

        return {
            "altitude": round(self.altitude, 2),
            "velocity": round(self.velocity, 2),
            "pressure": round(self.pressure, 1),
            "temperature": round(self.temperature, 1),
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "satellite_count": random.randint(5, 12),
            "fix_type": "3D",
            "battery": int(self.battery),
            "signal": int(self.signal),
            "roll": round(self.roll, 1),
            "pitch": round(self.pitch, 1),
            "yaw": round(self.yaw % 360, 1),
            "state": self.phase,
        }
