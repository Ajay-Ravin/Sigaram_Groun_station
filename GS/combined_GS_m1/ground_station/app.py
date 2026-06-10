"""
Ground Station — Main Application
Keeps the original sidebar + page navigation structure from old_grounstation,
upgraded with professional aerospace widgets.
"""
import sys
from typing import List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QGridLayout, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from ground_station.theme import Color, Style
from ground_station.models import (
    RocketTelemetry, CanSatTelemetry, RocketState, CanSatState,
    TelemetryDataInterface, MissionEvent,
)
from ground_station.widgets import (
    AeroGauge, AttitudeIndicator, TelemetryCard, EventLogWidget,
    StateBar, LiveGraph, StatusHeader,
)


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR — same pattern as old_grounstation
# ═══════════════════════════════════════════════════════════════

class SidebarWidget(QWidget):
    page_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {Color.BG_PRIMARY}, stop:1 {Color.BG_PANEL});
                border-right: 1px solid {Color.CYAN}40;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(6)

        self.nav_buttons = []
        for title, subtitle, pid in [
            ("OVERVIEW", "Combined Status", 0),
            ("ROCKET", "Flight Data", 1),
            ("CANSAT", "Deployment", 2),
        ]:
            btn = self._make_btn(title, subtitle, pid)
            layout.addWidget(btn)
            self.nav_buttons.append((btn, pid))
        self.highlight_button(0)
        layout.addStretch()

    def _make_btn(self, title, subtitle, pid):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(14, 10, 14, 10)
        l.setSpacing(2)
        t = QLabel(title)
        t.setFont(QFont("Menlo", 11, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {Color.CYAN};")
        s = QLabel(subtitle)
        s.setFont(QFont("Menlo", 8))
        s.setStyleSheet(f"color: {Color.TEXT_DIM};")
        l.addWidget(t)
        l.addWidget(s)
        w.setCursor(Qt.CursorShape.PointingHandCursor)
        w.mousePressEvent = lambda e: self._click(pid)
        return w

    def _click(self, pid):
        self.highlight_button(pid)
        self.page_selected.emit(pid)

    def highlight_button(self, pid):
        for btn, p in self.nav_buttons:
            if p == pid:
                btn.setStyleSheet(f"""
                    QWidget {{
                        background: {Color.BG_CARD};
                        border-left: 3px solid {Color.CYAN};
                        border-radius: 4px;
                    }}
                """)
            else:
                btn.setStyleSheet("background: transparent;")


# ═══════════════════════════════════════════════════════════════
#  OVERVIEW PAGE — rocket + cansat side by side
# ═══════════════════════════════════════════════════════════════

class OverviewPage(QWidget):
    def __init__(self, telem: TelemetryDataInterface):
        super().__init__()
        self.telem = telem

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{border:none;}")

        body = QWidget()
        lay = QHBoxLayout(body)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)

        # Left: Rocket
        self.r_col = self._build_rocket_col()
        lay.addWidget(self.r_col, 1)

        # Center: Event log
        self.event_log = EventLogWidget()
        self.event_log.setMinimumWidth(200)
        self.event_log.setMaximumWidth(260)
        lay.addWidget(self.event_log)

        # Right: CanSat
        self.c_col = self._build_cansat_col()
        lay.addWidget(self.c_col, 1)

        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        telem.rocket_updated.connect(self._on_rocket)
        telem.cansat_updated.connect(self._on_cansat)
        telem.event_logged.connect(lambda ev: self.event_log.add_event(ev))

    def _build_rocket_col(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)

        t = QLabel("ROCKET")
        t.setStyleSheet(f"color:{Color.CYAN}; font: bold 14px 'Menlo';")
        l.addWidget(t)

        self.r_state = StateBar([s.value for s in RocketState], Color.GREEN)
        l.addWidget(self.r_state)

        g = QGridLayout(); g.setSpacing(4)
        self.ro_alt = AeroGauge("ALT", "m", 0, 2000, 200)
        self.ro_vel = AeroGauge("VEL", "m/s", 0, 200, 20, warn_start=150, danger_start=170)
        self.ro_acc = AeroGauge("ACCEL", "g", -20, 20, 2)
        self.ro_tmp = AeroGauge("TEMP", "°C", -40, 80, 10)
        g.addWidget(self.ro_alt, 0, 0)
        g.addWidget(self.ro_vel, 0, 1)
        g.addWidget(self.ro_acc, 1, 0)
        g.addWidget(self.ro_tmp, 1, 1)
        l.addLayout(g)

        gg = QGridLayout(); gg.setSpacing(4)
        self.ro_g_alt = LiveGraph("Altitude", Color.CYAN)
        self.ro_g_vel = LiveGraph("Velocity", Color.GREEN)
        gg.addWidget(self.ro_g_alt, 0, 0)
        gg.addWidget(self.ro_g_vel, 0, 1)
        l.addLayout(gg)
        return w

    def _build_cansat_col(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)

        t = QLabel("CANSAT")
        t.setStyleSheet(f"color:{Color.CYAN}; font: bold 14px 'Menlo';")
        l.addWidget(t)

        self.c_state = StateBar([s.value for s in CanSatState], Color.BLUE)
        l.addWidget(self.c_state)

        g = QGridLayout(); g.setSpacing(4)
        self.co_alt = AeroGauge("ALT", "m", 0, 2000, 200)
        self.co_vel = AeroGauge("DESC", "m/s", 0, 50, 5, warn_start=35, danger_start=45)
        self.co_prs = AeroGauge("PRES", "Pa", 60000, 102000, 5000)
        self.co_tmp = AeroGauge("TEMP", "°C", -40, 80, 10)
        g.addWidget(self.co_alt, 0, 0)
        g.addWidget(self.co_vel, 0, 1)
        g.addWidget(self.co_prs, 1, 0)
        g.addWidget(self.co_tmp, 1, 1)
        l.addLayout(g)

        gg = QGridLayout(); gg.setSpacing(4)
        self.co_g_alt = LiveGraph("Altitude", Color.CYAN)
        self.co_g_prs = LiveGraph("Pressure", Color.AMBER)
        gg.addWidget(self.co_g_alt, 0, 0)
        gg.addWidget(self.co_g_prs, 0, 1)
        l.addLayout(gg)
        return w

    def _on_rocket(self, r):
        self.r_state.set_state(r.state.value)
        self.ro_alt.set_value(r.altitude)
        self.ro_vel.set_value(r.velocity)
        self.ro_acc.set_value(r.acceleration / 9.81)
        self.ro_tmp.set_value(r.temperature)
        self.ro_g_alt.add_point(r.altitude)
        self.ro_g_vel.add_point(r.velocity)

    def _on_cansat(self, c):
        self.c_state.set_state(c.state.value)
        self.co_alt.set_value(c.altitude)
        self.co_vel.set_value(abs(c.velocity))
        self.co_prs.set_value(c.pressure)
        self.co_tmp.set_value(c.temperature)
        self.co_g_alt.add_point(c.altitude)
        self.co_g_prs.add_point(c.pressure)


# ═══════════════════════════════════════════════════════════════
#  ROCKET DETAIL PAGE
# ═══════════════════════════════════════════════════════════════

class RocketDetailPage(QWidget):
    def __init__(self, telem: TelemetryDataInterface):
        super().__init__()
        self.telem = telem

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        t = QLabel("ROCKET TELEMETRY DETAIL")
        t.setStyleSheet(f"color:{Color.CYAN}; font: bold 14px 'Menlo';")
        lay.addWidget(t)

        self.state_bar = StateBar([s.value for s in RocketState], Color.GREEN)
        lay.addWidget(self.state_bar)

        # Row: gauges + attitude + telemetry card
        row1 = QHBoxLayout(); row1.setSpacing(8)
        g = QGridLayout(); g.setSpacing(4)
        self.g_alt = AeroGauge("ALTITUDE", "m", 0, 2000, 200)
        self.g_vel = AeroGauge("VELOCITY", "m/s", 0, 200, 20, warn_start=150, danger_start=170)
        self.g_acc = AeroGauge("ACCEL", "g", -20, 20, 2)
        self.g_prs = AeroGauge("PRESSURE", "Pa", 50000, 102000, 5000)
        self.g_tmp = AeroGauge("TEMP", "°C", -40, 80, 10)
        g.addWidget(self.g_alt, 0, 0); g.addWidget(self.g_vel, 0, 1); g.addWidget(self.g_acc, 0, 2)
        g.addWidget(self.g_prs, 1, 0); g.addWidget(self.g_tmp, 1, 1)

        gw = QWidget(); gw.setLayout(g)
        row1.addWidget(gw, 3)

        self.attitude = AttitudeIndicator("ROCKET ATTITUDE")
        row1.addWidget(self.attitude, 2)

        self.card = TelemetryCard("ROCKET DATA", [
            "Altitude", "Velocity", "Accel (g)", "Temp",
            "Pressure", "Latitude", "Longitude", "GPS Fix", "Phase",
        ])
        row1.addWidget(self.card, 2)
        lay.addLayout(row1)

        # Graphs
        gg = QGridLayout(); gg.setSpacing(4)
        self.gr_alt = LiveGraph("Altitude (m)", Color.CYAN)
        self.gr_vel = LiveGraph("Velocity (m/s)", Color.GREEN)
        self.gr_acc = LiveGraph("Acceleration (g)", Color.AMBER)
        self.gr_prs = LiveGraph("Pressure (Pa)", Color.AMBER)
        gg.addWidget(self.gr_alt, 0, 0); gg.addWidget(self.gr_vel, 0, 1)
        gg.addWidget(self.gr_acc, 1, 0); gg.addWidget(self.gr_prs, 1, 1)
        lay.addLayout(gg, 1)

        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        telem.rocket_updated.connect(self._update)

    def _update(self, r):
        self.state_bar.set_state(r.state.value)
        self.g_alt.set_value(r.altitude)
        self.g_vel.set_value(r.velocity)
        self.g_acc.set_value(r.acceleration / 9.81)
        self.g_prs.set_value(r.pressure)
        self.g_tmp.set_value(r.temperature)
        self.attitude.set_attitude(r.roll, r.pitch, r.yaw)

        pc = {
            "PRE": Color.AMBER, "IGN": Color.RED, "BOOST": Color.RED,
            "COAST": Color.CYAN, "APOGEE": Color.GREEN, "DESC": Color.BLUE,
        }
        self.card.set_field("Altitude", f"{r.altitude:.1f} m")
        self.card.set_field("Velocity", f"{r.velocity:.1f} m/s")
        self.card.set_field("Accel (g)", f"{r.acceleration / 9.81:.2f} g")
        self.card.set_field("Temp", f"{r.temperature:.1f} °C")
        self.card.set_field("Pressure", f"{r.pressure:.0f} Pa")
        self.card.set_field("Latitude", f"{r.latitude:.6f}°")
        self.card.set_field("Longitude", f"{r.longitude:.6f}°")
        self.card.set_field("GPS Fix", r.gps_fix)
        self.card.set_field("Phase", r.state.value, pc.get(r.state.value, Color.TEXT))

        self.gr_alt.add_point(r.altitude)
        self.gr_vel.add_point(r.velocity)
        self.gr_acc.add_point(r.acceleration / 9.81)
        self.gr_prs.add_point(r.pressure)


# ═══════════════════════════════════════════════════════════════
#  CANSAT DETAIL PAGE
# ═══════════════════════════════════════════════════════════════

class CanSatDetailPage(QWidget):
    def __init__(self, telem: TelemetryDataInterface):
        super().__init__()
        self.telem = telem

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        t = QLabel("CANSAT TELEMETRY DETAIL")
        t.setStyleSheet(f"color:{Color.CYAN}; font: bold 14px 'Menlo';")
        lay.addWidget(t)

        self.state_bar = StateBar([s.value for s in CanSatState], Color.BLUE)
        lay.addWidget(self.state_bar)

        # Row: gauges + attitude + card
        row1 = QHBoxLayout(); row1.setSpacing(8)
        g = QGridLayout(); g.setSpacing(4)
        self.g_alt = AeroGauge("ALTITUDE", "m", 0, 2000, 200)
        self.g_vel = AeroGauge("DESCENT", "m/s", 0, 50, 5, warn_start=35, danger_start=45)
        self.g_prs = AeroGauge("PRESSURE", "Pa", 60000, 102000, 5000)
        self.g_tmp = AeroGauge("TEMP", "°C", -40, 80, 10)
        g.addWidget(self.g_alt, 0, 0); g.addWidget(self.g_vel, 0, 1)
        g.addWidget(self.g_prs, 1, 0); g.addWidget(self.g_tmp, 1, 1)

        gw = QWidget(); gw.setLayout(g)
        row1.addWidget(gw, 3)

        self.attitude = AttitudeIndicator("CANSAT ATTITUDE")
        row1.addWidget(self.attitude, 2)

        self.card = TelemetryCard("CANSAT DATA", [
            "Altitude", "Descent", "Temp", "Pressure",
            "Latitude", "Longitude", "Satellites", "Fix", "Deploy",
        ])
        row1.addWidget(self.card, 2)
        lay.addLayout(row1)

        # Graphs
        gg = QGridLayout(); gg.setSpacing(4)
        self.gr_alt = LiveGraph("Altitude (m)", Color.CYAN)
        self.gr_vel = LiveGraph("Descent (m/s)", Color.GREEN)
        self.gr_prs = LiveGraph("Pressure (Pa)", Color.AMBER)
        self.gr_tmp = LiveGraph("Temperature (°C)", Color.BLUE)
        gg.addWidget(self.gr_alt, 0, 0); gg.addWidget(self.gr_vel, 0, 1)
        gg.addWidget(self.gr_prs, 1, 0); gg.addWidget(self.gr_tmp, 1, 1)
        lay.addLayout(gg, 1)

        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        telem.cansat_updated.connect(self._update)

    def _update(self, c):
        self.state_bar.set_state(c.state.value)
        self.g_alt.set_value(c.altitude)
        self.g_vel.set_value(abs(c.velocity))
        self.g_prs.set_value(c.pressure)
        self.g_tmp.set_value(c.temperature)
        self.attitude.set_attitude(c.roll, c.pitch, c.yaw)

        dc = Color.GREEN if c.state.value in ("DEPLOY","FALL","LAND","POST") else Color.AMBER
        self.card.set_field("Altitude", f"{c.altitude:.1f} m")
        self.card.set_field("Descent", f"{abs(c.velocity):.1f} m/s")
        self.card.set_field("Temp", f"{c.temperature:.1f} °C")
        self.card.set_field("Pressure", f"{c.pressure:.0f} Pa")
        self.card.set_field("Latitude", f"{c.latitude:.6f}°")
        self.card.set_field("Longitude", f"{c.longitude:.6f}°")
        self.card.set_field("Satellites", f"{c.satellite_count}")
        self.card.set_field("Fix", c.fix_type, Color.GREEN if c.fix_type == "3D" else Color.AMBER)
        self.card.set_field("Deploy", c.state.value, dc)

        self.gr_alt.add_point(c.altitude)
        self.gr_vel.add_point(abs(c.velocity))
        self.gr_prs.add_point(c.pressure)
        self.gr_tmp.add_point(c.temperature)


# ═══════════════════════════════════════════════════════════════
#  MAIN APPLICATION — same structure as old_grounstation
# ═══════════════════════════════════════════════════════════════

class GroundStationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CANSAT & ROCKET GROUND STATION")
        self.setMinimumSize(1500, 950)

        screen = QApplication.primaryScreen()
        if screen:
            g = screen.geometry()
            self.move((g.width() - 1500) // 2, (g.height() - 950) // 2)

        # Telemetry interface
        self.telem = TelemetryDataInterface()

        # Main container
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Status header
        self.header = StatusHeader()
        main_layout.addWidget(self.header)

        # Content area: sidebar + pages
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.sidebar.page_selected.connect(self._on_page)
        content.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.overview_page = OverviewPage(self.telem)
        self.rocket_page = RocketDetailPage(self.telem)
        self.cansat_page = CanSatDetailPage(self.telem)
        self.pages.addWidget(self.overview_page)
        self.pages.addWidget(self.rocket_page)
        self.pages.addWidget(self.cansat_page)
        content.addWidget(self.pages)

        main_layout.addLayout(content)
        self.setCentralWidget(main_widget)

        # Theme
        self.setStyleSheet(f"""
            QMainWindow {{ background: {Color.BG_PRIMARY}; }}
            QWidget {{ color: {Color.TEXT}; }}
            QScrollBar:vertical {{
                background: {Color.BG_PRIMARY}; width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {Color.BORDER}; border-radius: 3px;
            }}
        """)

        # Header refresh timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(500)

    def _on_page(self, pid):
        self.pages.setCurrentIndex(pid)
        self.sidebar.highlight_button(pid)

    def _refresh(self):
        self.header.update_header(self.telem.rocket, self.telem.cansat,
                                  self.telem.elapsed_time)

    # Public API — same as old_grounstation
    def receive_rocket_telemetry(self, t: RocketTelemetry):
        self.telem.update_rocket(t)

    def receive_cansat_telemetry(self, t: CanSatTelemetry):
        self.telem.update_cansat(t)

    def receive_elapsed_time(self, s: float):
        self.telem.update_elapsed(s)
