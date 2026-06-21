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
    QComboBox, QTextEdit, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor


try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    QWebEngineView = None

from ground_station.theme import Color, Style
from ground_station.models import (
    RocketTelemetry, CanSatTelemetry, RocketState, CanSatState,
    TelemetryDataInterface, MissionEvent,
)
from ground_station.widgets import (
    AeroGauge, AttitudeIndicator, TelemetryCard, EventLogWidget,
    StateBar, LiveGraph, StatusHeader,
)
from ground_station.serial_reader import SerialReaderThread


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
            ("COM MONITOR", "Raw Serial Data", 3),
            ("COMMAND", "Command Console", 4),
            ("SIMULATION", "Test Mode", 5),
        ]:
            btn = self._make_btn(title, subtitle, pid)
            layout.addWidget(btn)
            self.nav_buttons.append((btn, pid))
        self.highlight_button(0)
        
        layout.addStretch()

        # COM Port Option Section in Sidebar
        com_widget = QWidget()
        com_layout = QVBoxLayout(com_widget)
        com_layout.setContentsMargins(14, 10, 14, 10)
        com_layout.setSpacing(4)

        lbl = QLabel("COM PORT SELECT")
        lbl.setFont(QFont("Menlo", 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {Color.TEXT_DIM};")
        com_layout.addWidget(lbl)

        self.com_dropdown = QComboBox()
        self.com_dropdown.addItems(["Select COM...", "COM3 (Avionics)", "COM4 (CanSat)"])
        self.com_dropdown.setStyleSheet(f"""
            QComboBox {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT};
                border: 1px solid {Color.BORDER};
                border-radius: 4px;
                padding: 4px 6px;
                font-family: 'Menlo', monospace;
                font-size: 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT};
                selection-background-color: {Color.BG_CARD_HOVER};
            }}
        """)
        com_layout.addWidget(self.com_dropdown)
        layout.addWidget(com_widget)

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

        # Right: CanSat
        self.c_col = self._build_cansat_col()
        lay.addWidget(self.c_col, 1)

        # Far Right Panel: Event log (grows vertically as events are added)
        right_panel = QWidget()
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        self.event_log = EventLogWidget()
        self.event_log.setMinimumWidth(200)
        self.event_log.setMaximumWidth(260)
        right_lay.addWidget(self.event_log)
        right_lay.addStretch()

        lay.addWidget(right_panel)

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
            "Boot": Color.TEXT_DIM,
            "Pre_launch": Color.AMBER,
            "ascent": Color.RED,
            "Deployment": Color.CYAN,
            "Descent": Color.BLUE,
            "Impact/recovery": Color.GREEN,
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


class ComMonitorPage(QWidget):
    def __init__(self, telem: TelemetryDataInterface):
        super().__init__()
        self.telem = telem
        self.active_data_tab = "rocket"
        self.rocket_connected = False
        self.cansat_connected = False
        self.r_thread = None
        self.c_thread = None

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 12, 12, 12)
        main_lay.setSpacing(10)

        # Title
        title = QLabel("COM PORT & RAW DATA MONITOR")
        title.setStyleSheet(f"color: {Color.CYAN}; font: bold 16px 'Menlo';")
        main_lay.addWidget(title)

        # ── Top Control Bar: Rocket COM | CanSat COM ──
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
            }}
        """)
        ctrl_lay = QHBoxLayout(ctrl_frame)
        ctrl_lay.setContentsMargins(12, 8, 12, 8)
        ctrl_lay.setSpacing(8)

        # Rocket COM config
        r_lbl = QLabel("🚀 ROCKET")
        r_lbl.setStyleSheet(f"color: {Color.CYAN}; font: bold 10px 'Menlo';")
        ctrl_lay.addWidget(r_lbl)

        self.r_port = QComboBox()
        self.r_port.addItems(["COM3", "COM1", "COM5", "COM6", "COM7"])
        self.r_port.setStyleSheet(self._combo_css())
        self.r_port.setFixedWidth(75)
        ctrl_lay.addWidget(self.r_port)

        self.r_baud = QComboBox()
        self.r_baud.addItems(["115200", "9600", "57600", "38400"])
        self.r_baud.setStyleSheet(self._combo_css())
        self.r_baud.setFixedWidth(75)
        ctrl_lay.addWidget(self.r_baud)

        self.r_conn_btn = QPushButton("● LIVE")
        self.r_conn_btn.clicked.connect(lambda: self._toggle_conn("rocket"))
        self.r_conn_btn.setStyleSheet(self._conn_css(True))
        ctrl_lay.addWidget(self.r_conn_btn)

        # Vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {Color.BORDER};")
        sep.setFixedWidth(2)
        ctrl_lay.addWidget(sep)

        # CanSat COM config
        c_lbl = QLabel("📡 CANSAT")
        c_lbl.setStyleSheet(f"color: {Color.CYAN}; font: bold 10px 'Menlo';")
        ctrl_lay.addWidget(c_lbl)

        self.c_port = QComboBox()
        self.c_port.addItems(["COM4", "COM2", "COM8", "COM9", "COM10"])
        self.c_port.setStyleSheet(self._combo_css())
        self.c_port.setFixedWidth(75)
        ctrl_lay.addWidget(self.c_port)

        self.c_baud = QComboBox()
        self.c_baud.addItems(["115200", "9600", "57600", "38400"])
        self.c_baud.setStyleSheet(self._combo_css())
        self.c_baud.setFixedWidth(75)
        ctrl_lay.addWidget(self.c_baud)

        self.c_conn_btn = QPushButton("● LIVE")
        self.c_conn_btn.clicked.connect(lambda: self._toggle_conn("cansat"))
        self.c_conn_btn.setStyleSheet(self._conn_css(True))
        ctrl_lay.addWidget(self.c_conn_btn)

        ctrl_lay.addStretch()
        main_lay.addWidget(ctrl_frame)

        # ── Dual Terminals Side by Side ──
        term_lay = QHBoxLayout()
        term_lay.setSpacing(8)

        # Rocket terminal
        r_col = QVBoxLayout()
        r_hdr = QLabel("🚀 ROCKET SERIAL OUTPUT")
        r_hdr.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 9px 'Menlo';")
        r_col.addWidget(r_hdr)
        self.r_terminal = QTextEdit()
        self.r_terminal.setReadOnly(True)
        self.r_terminal.setStyleSheet(self._term_css("#00FF55"))
        r_col.addWidget(self.r_terminal, 1)
        r_clr = QPushButton("CLEAR")
        r_clr.clicked.connect(self.r_terminal.clear)
        r_clr.setStyleSheet(self._sm_btn_css())
        r_col.addWidget(r_clr)
        term_lay.addLayout(r_col, 1)

        # CanSat terminal
        c_col = QVBoxLayout()
        c_hdr = QLabel("📡 CANSAT SERIAL OUTPUT")
        c_hdr.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 9px 'Menlo';")
        c_col.addWidget(c_hdr)
        self.c_terminal = QTextEdit()
        self.c_terminal.setReadOnly(True)
        self.c_terminal.setStyleSheet(self._term_css("#00D4FF"))
        c_col.addWidget(self.c_terminal, 1)
        c_clr = QPushButton("CLEAR")
        c_clr.clicked.connect(self.c_terminal.clear)
        c_clr.setStyleSheet(self._sm_btn_css())
        c_col.addWidget(c_clr)
        term_lay.addLayout(c_col, 1)

        main_lay.addLayout(term_lay, 3)

        # ── Bottom: GPS Map + Raw Data ──
        bottom_lay = QHBoxLayout()
        bottom_lay.setSpacing(8)

        # GPS Location widget
        gps_col = QVBoxLayout()
        gps_hdr = QLabel("📍 GPS LOCATION")
        gps_hdr.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 9px 'Menlo';")
        gps_col.addWidget(gps_hdr)
        self._init_map(gps_col)
        bottom_lay.addLayout(gps_col, 3)

        # Raw data panel with sub-tabs
        raw_col = QVBoxLayout()
        raw_col.setSpacing(4)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        self.rocket_tab = QPushButton("🚀 ROCKET")
        self.rocket_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rocket_tab.clicked.connect(lambda: self._set_data_tab("rocket"))
        tab_row.addWidget(self.rocket_tab)
        self.cansat_tab = QPushButton("📡 CANSAT")
        self.cansat_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cansat_tab.clicked.connect(lambda: self._set_data_tab("cansat"))
        tab_row.addWidget(self.cansat_tab)
        raw_col.addLayout(tab_row)
        self._refresh_tab_style()

        raw_scroll = QScrollArea()
        raw_scroll.setWidgetResizable(True)
        raw_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.grid_w = QWidget()
        self.grid_lay = QGridLayout(self.grid_w)
        self.grid_lay.setSpacing(6)
        self.grid_lay.setContentsMargins(0, 0, 0, 0)
        raw_scroll.setWidget(self.grid_w)
        raw_col.addWidget(raw_scroll, 1)

        bottom_lay.addLayout(raw_col, 4)
        main_lay.addLayout(bottom_lay, 2)

        self._build_grid()
        self.telem.rocket_updated.connect(self._on_rocket)
        self.telem.cansat_updated.connect(self._on_cansat)

    # ── Map ──
    def _init_map(self, parent_layout):
        if HAS_WEBENGINE:
            self.map_view = QWebEngineView()
            self.map_view.setMinimumHeight(160)
            self.map_view.setHtml(self._map_html())
            parent_layout.addWidget(self.map_view, 1)
            self._map_ok = False
            self.map_view.loadFinished.connect(lambda ok: setattr(self, '_map_ok', ok))
        else:
            self.map_view = None
            box = QFrame()
            box.setStyleSheet(f"""
                QFrame {{
                    background-color: {Color.BG_CARD};
                    border: 1px solid {Color.BORDER};
                    border-radius: 6px;
                }}
            """)
            box.setMinimumHeight(160)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(12, 10, 12, 10)
            bl.setSpacing(4)

            rl = QLabel("🚀 ROCKET POSITION")
            rl.setStyleSheet(f"color: {Color.CYAN}; font: bold 10px 'Menlo';")
            bl.addWidget(rl)
            self.r_lat_lbl = QLabel("LAT: —")
            self.r_lat_lbl.setStyleSheet(f"color: {Color.TEXT}; font: bold 13px 'Menlo';")
            self.r_lon_lbl = QLabel("LON: —")
            self.r_lon_lbl.setStyleSheet(f"color: {Color.TEXT}; font: bold 13px 'Menlo';")
            bl.addWidget(self.r_lat_lbl)
            bl.addWidget(self.r_lon_lbl)

            s = QFrame()
            s.setFrameShape(QFrame.Shape.HLine)
            s.setStyleSheet(f"color: {Color.BORDER};")
            bl.addWidget(s)

            cl = QLabel("📡 CANSAT POSITION")
            cl.setStyleSheet(f"color: {Color.CYAN}; font: bold 10px 'Menlo';")
            bl.addWidget(cl)
            self.c_lat_lbl = QLabel("LAT: —")
            self.c_lat_lbl.setStyleSheet(f"color: {Color.TEXT}; font: bold 13px 'Menlo';")
            self.c_lon_lbl = QLabel("LON: —")
            self.c_lon_lbl.setStyleSheet(f"color: {Color.TEXT}; font: bold 13px 'Menlo';")
            bl.addWidget(self.c_lat_lbl)
            bl.addWidget(self.c_lon_lbl)
            bl.addStretch()
            parent_layout.addWidget(box, 1)

    def _map_html(self):
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>'
            '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
            '<style>body{margin:0;background:#080E1A;}#map{width:100%;height:100vh;}'
            '.leaflet-control-attribution{display:none;}</style>'
            '</head><body><div id="map"></div><script>'
            "var map=L.map('map',{zoomControl:false}).setView([34.0522,-118.2437],15);"
            "L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',"
            "{maxZoom:19}).addTo(map);"
            "var rI=L.divIcon({className:'',html:'<div style=\"background:#FF3344;"
            "width:12px;height:12px;border-radius:50%;border:2px solid #fff;\"></div>',"
            "iconSize:[16,16],iconAnchor:[8,8]});"
            "var cI=L.divIcon({className:'',html:'<div style=\"background:#00D4FF;"
            "width:12px;height:12px;border-radius:50%;border:2px solid #fff;\"></div>',"
            "iconSize:[16,16],iconAnchor:[8,8]});"
            "var rM=L.marker([34.0522,-118.2437],{icon:rI}).addTo(map).bindTooltip('Rocket');"
            "var cM=L.marker([34.0525,-118.2440],{icon:cI}).addTo(map).bindTooltip('CanSat');"
            "var rT=L.polyline([],{color:'#FF3344',weight:2,opacity:0.7}).addTo(map);"
            "var cT=L.polyline([],{color:'#00D4FF',weight:2,opacity:0.7}).addTo(map);"
            "function updateR(a,b){rM.setLatLng([a,b]);rT.addLatLng([a,b]);map.panTo([a,b]);}"
            "function updateC(a,b){cM.setLatLng([a,b]);cT.addLatLng([a,b]);}"
            '</script></body></html>'
        )

    def _update_gps(self, src, lat, lon):
        if self.map_view and HAS_WEBENGINE and self._map_ok:
            js = f"updateR({lat},{lon})" if src == "rocket" else f"updateC({lat},{lon})"
            self.map_view.page().runJavaScript(js)
        elif not HAS_WEBENGINE and self.map_view is None:
            if src == "rocket":
                self.r_lat_lbl.setText(f"LAT: {lat:.6f}°")
                self.r_lon_lbl.setText(f"LON: {lon:.6f}°")
            else:
                self.c_lat_lbl.setText(f"LAT: {lat:.6f}°")
                self.c_lon_lbl.setText(f"LON: {lon:.6f}°")

    # ── Styles ──
    def _combo_css(self):
        return f"""
            QComboBox {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT};
                border: 1px solid {Color.BORDER};
                border-radius: 4px;
                padding: 3px 6px;
                font: 10px 'Menlo';
            }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT};
                selection-background-color: {Color.BG_CARD_HOVER};
                border: 1px solid {Color.BORDER};
            }}
        """

    def _conn_css(self, on):
        bg = Color.GREEN_DIM if on else Color.RED_DIM
        bd = Color.GREEN if on else Color.RED
        hv = Color.GREEN if on else Color.RED
        return f"""
            QPushButton {{
                background-color: {bg};
                color: #fff;
                border: 1px solid {bd};
                border-radius: 4px;
                padding: 3px 10px;
                font: bold 10px 'Menlo';
            }}
            QPushButton:hover {{ background-color: {hv}; }}
        """

    def _term_css(self, color):
        return f"""
            QTextEdit {{
                background-color: {Color.BG_PANEL};
                color: {color};
                font-family: 'Consolas','Menlo','Courier New',monospace;
                font-size: 10px;
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
                padding: 6px;
            }}
        """

    def _sm_btn_css(self):
        return f"""
            QPushButton {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT_DIM};
                border: 1px solid {Color.BORDER};
                border-radius: 3px;
                padding: 2px 8px;
                font: 9px 'Menlo';
            }}
            QPushButton:hover {{
                background-color: {Color.BG_CARD_HOVER};
                color: {Color.TEXT};
            }}
        """

    def _refresh_tab_style(self):
        on = f"""
            QPushButton {{
                background-color: {Color.CYAN_DIM};
                color: #fff;
                border: 1px solid {Color.CYAN};
                border-radius: 4px;
                padding: 4px 12px;
                font: bold 10px 'Menlo';
            }}
        """
        off = f"""
            QPushButton {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT_DIM};
                border: 1px solid {Color.BORDER};
                border-radius: 4px;
                padding: 4px 12px;
                font: bold 10px 'Menlo';
            }}
            QPushButton:hover {{
                background-color: {Color.BG_CARD_HOVER};
                color: {Color.TEXT};
            }}
        """
        self.rocket_tab.setStyleSheet(on if self.active_data_tab == "rocket" else off)
        self.cansat_tab.setStyleSheet(off if self.active_data_tab == "rocket" else on)

    def _set_data_tab(self, tab):
        self.active_data_tab = tab
        self._refresh_tab_style()
        self._build_grid()

    def _toggle_conn(self, src):
        if src == "rocket":
            if not self.rocket_connected:
                # Connect
                port = self.r_port.currentText()
                baud = int(self.r_baud.currentText())
                self.r_thread = SerialReaderThread(port, baud, source_type="ROCKET")
                self.r_thread.rocket_data_received.connect(self._handle_rocket_dict)
                self.r_thread.log_message.connect(self.r_terminal.append)
                self.r_thread.connection_error.connect(self.r_terminal.append)
                self.r_thread.start()
                self.rocket_connected = True
            else:
                # Disconnect
                if self.r_thread:
                    self.r_thread.stop()
                    self.r_thread = None
                self.rocket_connected = False
                
            self.r_conn_btn.setText("● LIVE" if self.rocket_connected else "○ OFF")
            self.r_conn_btn.setStyleSheet(self._conn_css(self.rocket_connected))
            
        else:
            if not self.cansat_connected:
                # Connect
                port = self.c_port.currentText()
                baud = int(self.c_baud.currentText())
                self.c_thread = SerialReaderThread(port, baud, source_type="CANSAT")
                self.c_thread.cansat_data_received.connect(self._handle_cansat_dict)
                self.c_thread.log_message.connect(self.c_terminal.append)
                self.c_thread.connection_error.connect(self.c_terminal.append)
                self.c_thread.start()
                self.cansat_connected = True
            else:
                # Disconnect
                if self.c_thread:
                    self.c_thread.stop()
                    self.c_thread = None
                self.cansat_connected = False

            self.c_conn_btn.setText("● LIVE" if self.cansat_connected else "○ OFF")
            self.c_conn_btn.setStyleSheet(self._conn_css(self.cansat_connected))

    def _handle_rocket_dict(self, data: dict):
        # Pop mission_time before constructing the dataclass
        mission_time = data.pop("mission_time", None)
        if "source" in data:
            del data["source"]
        rt = RocketTelemetry(**data)
        self.telem.update_rocket(rt)
        if mission_time is not None:
            self.telem.update_elapsed(mission_time)

    def _handle_cansat_dict(self, data: dict):
        # Pop mission_time before constructing the dataclass
        mission_time = data.pop("mission_time", None)
        if "source" in data:
            del data["source"]
        ct = CanSatTelemetry(**data)
        self.telem.update_cansat(ct)
        if mission_time is not None:
            self.telem.update_elapsed(mission_time)

    # ── Data Grid ──
    def _build_grid(self):
        while self.grid_lay.count():
            it = self.grid_lay.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        self.data_widgets = {}
        if self.active_data_tab == "rocket":
            fields = [
                ("Altitude", "m"), ("Velocity", "m/s"),
                ("Acceleration", "m/s²"), ("Temperature", "°C"),
                ("Pressure", "Pa"), ("Lat, Lon", "°"),
                ("GPS Fix", ""), ("Battery", "%"),
                ("Signal", "dBm"), ("Roll", "°"),
                ("Pitch", "°"), ("Yaw", "°"),
                ("Flight State", ""),
            ]
        else:
            fields = [
                ("Altitude", "m"), ("Velocity", "m/s"),
                ("Pressure", "Pa"), ("Temperature", "°C"),
                ("Lat, Lon", "°"), ("Satellites", ""),
                ("Fix Type", ""), ("Battery", "%"),
                ("Signal", "dBm"), ("Roll", "°"),
                ("Pitch", "°"), ("Yaw", "°"),
                ("Deploy State", ""),
            ]
        cols = 3
        for idx, (name, unit) in enumerate(fields):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Color.BG_CARD};
                    border: 1px solid {Color.BORDER};
                    border-radius: 6px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 6, 8, 6)
            cl.setSpacing(2)
            nl = QLabel(name.upper())
            nl.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 8px 'Menlo';")
            vl = QLabel("—")
            vl.setStyleSheet(f"color: {Color.TEXT}; font: bold 14px 'Menlo';")
            ul = QLabel(unit)
            ul.setStyleSheet(f"color: {Color.TEXT_DIM}; font: 7px 'Menlo';")
            cl.addWidget(nl)
            cl.addWidget(vl)
            if unit:
                cl.addWidget(ul)
            self.grid_lay.addWidget(card, idx // cols, idx % cols)
            self.data_widgets[name] = vl

    # ── Telemetry ──
    def _on_rocket(self, r):
        if not self.rocket_connected:
            return
        line = (f"[$AV] ALT:{r.altitude:.2f} VEL:{r.velocity:.2f} "
                f"ACC:{r.acceleration:.2f} T:{r.temperature:.1f} "
                f"P:{r.pressure:.1f} STATE:{r.state.value}")
        self._push(self.r_terminal, line)
        self._update_gps("rocket", r.latitude, r.longitude)
        if self.active_data_tab == "rocket":
            self._val("Altitude", f"{r.altitude:.2f}")
            self._val("Velocity", f"{r.velocity:.2f}")
            self._val("Acceleration", f"{r.acceleration:.2f}")
            self._val("Temperature", f"{r.temperature:.1f}")
            self._val("Pressure", f"{r.pressure:.1f}")
            self._val("Lat, Lon", f"{r.latitude:.6f}, {r.longitude:.6f}")
            self._val("GPS Fix", r.gps_fix)
            self._val("Battery", f"{r.battery}")
            self._val("Signal", f"{r.signal}")
            self._val("Roll", f"{r.roll:.1f}")
            self._val("Pitch", f"{r.pitch:.1f}")
            self._val("Yaw", f"{r.yaw:.1f}")
            self._val("Flight State", r.state.value)

    def _on_cansat(self, c):
        if not self.cansat_connected:
            return
        line = (f"[$CS] ALT:{c.altitude:.2f} VEL:{c.velocity:.2f} "
                f"P:{c.pressure:.1f} T:{c.temperature:.1f} "
                f"SAT:{c.satellite_count} STATE:{c.state.value}")
        self._push(self.c_terminal, line)
        self._update_gps("cansat", c.latitude, c.longitude)
        if self.active_data_tab == "cansat":
            self._val("Altitude", f"{c.altitude:.2f}")
            self._val("Velocity", f"{c.velocity:.2f}")
            self._val("Pressure", f"{c.pressure:.1f}")
            self._val("Temperature", f"{c.temperature:.1f}")
            self._val("Lat, Lon", f"{c.latitude:.6f}, {c.longitude:.6f}")
            self._val("Satellites", f"{c.satellite_count}")
            self._val("Fix Type", c.fix_type)
            self._val("Battery", f"{c.battery}")
            self._val("Signal", f"{c.signal}")
            self._val("Roll", f"{c.roll:.1f}")
            self._val("Pitch", f"{c.pitch:.1f}")
            self._val("Yaw", f"{c.yaw:.1f}")
            self._val("Deploy State", c.state.value)

    def _val(self, k, v):
        if k in self.data_widgets:
            self.data_widgets[k].setText(v)

    def _push(self, term, line):
        term.append(line)
        doc = term.document()
        if doc.lineCount() > 200:
            cur = term.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start)
            cur.movePosition(QTextCursor.MoveOperation.Down,
                             QTextCursor.MoveMode.KeepAnchor,
                             doc.lineCount() - 200)
            cur.removeSelectedText()
        term.verticalScrollBar().setValue(term.verticalScrollBar().maximum())


# ═══════════════════════════════════════════════════════════════
#  COMMAND CONSOLE PAGE
# ═══════════════════════════════════════════════════════════════

class CommandConsolePage(QWidget):
    """Command console for sending serial commands to the rocket/CanSat."""

    # Command definitions: (category, [(label, serial_command), ...])
    COMMANDS = [
        ("Calibration", [
            ("Zero IMU", "CMD,ZERO_IMU"),
            ("Set Ground Pressure", "CMD,SET_GROUND_PRESSURE"),
        ]),
        ("Flight", [
            ("ARM", "CMD,ARM"),
            ("DISARM", "CMD,DISARM"),
            ("TEST MODE", "CMD,TEST_MODE"),
            ("RESET", "CMD,RESET"),
        ]),
        ("Recovery", [
            ("Payload Servo", "CMD,PAYLOAD_SERVO"),
            ("Recovery Servo", "CMD,RECOVERY_SERVO"),
            ("Buzzer", "CMD,BUZZER"),
        ]),
        ("Telemetry", [
            ("Ping", "CMD,PING"),
            ("Status", "CMD,STATUS"),
            ("Start Log", "CMD,START_LOG"),
            ("Stop Log", "CMD,STOP_LOG"),
        ]),
        ("Storage", [
            ("SD Status", "CMD,SD_STATUS"),
        ]),
        ("Diagnostics", [
            ("Self Test", "CMD,SELF_TEST"),
        ]),
    ]

    def __init__(self, telem: TelemetryDataInterface, window=None):
        super().__init__()
        self.telem = telem
        self.window = window

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{border:none;}")

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # Title
        title = QLabel("COMMAND CONSOLE")
        title.setStyleSheet(f"color: {Color.CYAN}; font: bold 16px 'Menlo';")
        lay.addWidget(title)

        # Target selector
        target_row = QHBoxLayout()
        target_row.setSpacing(6)
        tgt_lbl = QLabel("TARGET:")
        tgt_lbl.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 10px 'Menlo';")
        target_row.addWidget(tgt_lbl)
        self.target_combo = QComboBox()
        self.target_combo.addItems(["Rocket", "CanSat"])
        self.target_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT};
                border: 1px solid {Color.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font: 10px 'Menlo';
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT};
                selection-background-color: {Color.BG_CARD_HOVER};
            }}
        """)
        target_row.addWidget(self.target_combo)
        target_row.addStretch()
        lay.addLayout(target_row)

        # Command sections
        for category, commands in self.COMMANDS:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Color.BG_CARD};
                    border: 1px solid {Color.BORDER};
                    border-radius: 6px;
                }}
            """)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(10, 8, 10, 8)
            fl.setSpacing(6)

            cat_lbl = QLabel(category.upper())
            cat_lbl.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 9px 'Menlo';")
            fl.addWidget(cat_lbl)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)
            for label, cmd in commands:
                btn = QPushButton(label)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Color.BG_CARD_HOVER};
                        color: {Color.TEXT};
                        border: 1px solid {Color.BORDER};
                        border-radius: 4px;
                        padding: 6px 12px;
                        font: bold 10px 'Menlo';
                    }}
                    QPushButton:hover {{
                        background-color: {Color.CYAN_DIM};
                        border-color: {Color.CYAN};
                        color: #fff;
                    }}
                    QPushButton:pressed {{
                        background-color: {Color.CYAN};
                    }}
                """)
                btn.clicked.connect(lambda checked, c=cmd: self._send_command(c))
                btn_row.addWidget(btn)
            btn_row.addStretch()
            fl.addLayout(btn_row)
            lay.addWidget(frame)

        # Console Output
        out_lbl = QLabel("CONSOLE OUTPUT")
        out_lbl.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 9px 'Menlo';")
        lay.addWidget(out_lbl)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Color.BG_PANEL};
                color: #00FF88;
                font-family: 'Consolas','Menlo','Courier New',monospace;
                font-size: 11px;
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        lay.addWidget(self.console_output, 1)

        # Clear button
        clr_btn = QPushButton("CLEAR CONSOLE")
        clr_btn.clicked.connect(self.console_output.clear)
        clr_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.BG_CARD};
                color: {Color.TEXT_DIM};
                border: 1px solid {Color.BORDER};
                border-radius: 3px;
                padding: 4px 10px;
                font: 9px 'Menlo';
            }}
            QPushButton:hover {{
                background-color: {Color.BG_CARD_HOVER};
                color: {Color.TEXT};
            }}
        """)
        lay.addWidget(clr_btn)

        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _send_command(self, cmd_str):
        """Send a command over the active serial connection."""
        if not self.window:
            self.console_output.append("> No window reference")
            return

        target = self.target_combo.currentText()
        com_page = self.window.com_monitor_page

        thread = com_page.r_thread if target == "Rocket" else com_page.c_thread
        connected = com_page.rocket_connected if target == "Rocket" else com_page.cansat_connected

        if not connected or not thread:
            self.console_output.append(
                f"> No active {target} connection. Connect via COM Monitor first."
            )
            return

        ok = thread.send_command(cmd_str)
        if ok:
            self.console_output.append(f"> Sent to {target}: {cmd_str}")
        else:
            self.console_output.append(f"> Failed to send to {target}: port not open")


# ═══════════════════════════════════════════════════════════════
#  SIMULATION PAGE
# ═══════════════════════════════════════════════════════════════

class SimulationPage(QWidget):
    """Manual simulation mode — user explicitly starts/stops simulated telemetry."""

    def __init__(self, telem: TelemetryDataInterface, window=None):
        super().__init__()
        self.telem = telem
        self.window = window
        self.rocket_running = False
        self.cansat_running = False
        self.rocket_paused = False
        self.cansat_paused = False
        self._r_timer = None
        self._c_timer = None
        self._r_sim = None
        self._c_sim = None
        self._r_pkt_count = 0
        self._c_pkt_count = 0

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 12, 12, 12)
        main_lay.setSpacing(12)

        title = QLabel("SIMULATION MODE")
        title.setStyleSheet(f"color: {Color.CYAN}; font: bold 16px 'Menlo';")
        main_lay.addWidget(title)

        desc = QLabel(
            "Manually start simulated telemetry to test the GUI without hardware.\n"
            "Simulation feeds data into the same pipeline as real serial data."
        )
        desc.setStyleSheet(f"color: {Color.TEXT_DIM}; font: 10px 'Menlo';")
        desc.setWordWrap(True)
        main_lay.addWidget(desc)

        # ── Master Controls ──
        m_frame = QFrame()
        m_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
            }}
        """)
        m_lay = QVBoxLayout(m_frame)
        m_lay.setContentsMargins(12, 10, 12, 10)
        m_lay.setSpacing(8)

        m_title = QLabel("🎛️ MASTER CONTROLS")
        m_title.setStyleSheet(f"color: {Color.CYAN}; font: bold 12px 'Menlo';")
        m_lay.addWidget(m_title)

        m_btn_row = QHBoxLayout()
        m_btn_row.setSpacing(8)

        self.m_start_btn = QPushButton("▶ Start Both")
        self.m_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.m_start_btn.clicked.connect(self._start_both)
        self.m_start_btn.setStyleSheet(self._btn_css(Color.GREEN))
        m_btn_row.addWidget(self.m_start_btn)

        self.m_pause_btn = QPushButton("⏸ Pause Both")
        self.m_pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.m_pause_btn.clicked.connect(self._pause_both)
        self.m_pause_btn.setStyleSheet(self._btn_css(Color.AMBER))
        m_btn_row.addWidget(self.m_pause_btn)

        self.m_stop_btn = QPushButton("■ Stop Both")
        self.m_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.m_stop_btn.clicked.connect(self._stop_both)
        self.m_stop_btn.setStyleSheet(self._btn_css(Color.RED))
        m_btn_row.addWidget(self.m_stop_btn)
        m_btn_row.addStretch()
        m_lay.addLayout(m_btn_row)
        main_lay.addWidget(m_frame)

        # ── Rocket Simulation ──
        r_frame = QFrame()
        r_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
            }}
        """)
        r_lay = QVBoxLayout(r_frame)
        r_lay.setContentsMargins(12, 10, 12, 10)
        r_lay.setSpacing(8)

        r_title = QLabel("🚀 ROCKET SIMULATION")
        r_title.setStyleSheet(f"color: {Color.CYAN}; font: bold 12px 'Menlo';")
        r_lay.addWidget(r_title)

        self.r_status = QLabel("○ STOPPED")
        self.r_status.setStyleSheet(f"color: {Color.RED}; font: bold 11px 'Menlo';")
        r_lay.addWidget(self.r_status)

        r_btn_row = QHBoxLayout()
        r_btn_row.setSpacing(8)
        self.r_start_btn = QPushButton("▶ Start Rocket Sim")
        self.r_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.r_start_btn.clicked.connect(self._start_rocket_sim)
        self.r_start_btn.setStyleSheet(self._btn_css(Color.GREEN))
        r_btn_row.addWidget(self.r_start_btn)

        self.r_pause_btn = QPushButton("⏸ Pause")
        self.r_pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.r_pause_btn.clicked.connect(self._pause_rocket_sim)
        self.r_pause_btn.setStyleSheet(self._btn_css(Color.AMBER))
        r_btn_row.addWidget(self.r_pause_btn)

        self.r_stop_btn = QPushButton("■ Stop Rocket Sim")
        self.r_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.r_stop_btn.clicked.connect(self._stop_rocket_sim)
        self.r_stop_btn.setStyleSheet(self._btn_css(Color.RED))
        r_btn_row.addWidget(self.r_stop_btn)
        r_btn_row.addStretch()
        r_lay.addLayout(r_btn_row)
        main_lay.addWidget(r_frame)

        # ── CanSat Simulation ──
        c_frame = QFrame()
        c_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
            }}
        """)
        c_lay = QVBoxLayout(c_frame)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(8)

        c_title = QLabel("📡 CANSAT SIMULATION")
        c_title.setStyleSheet(f"color: {Color.CYAN}; font: bold 12px 'Menlo';")
        c_lay.addWidget(c_title)

        self.c_status = QLabel("○ STOPPED")
        self.c_status.setStyleSheet(f"color: {Color.RED}; font: bold 11px 'Menlo';")
        c_lay.addWidget(self.c_status)

        c_btn_row = QHBoxLayout()
        c_btn_row.setSpacing(8)
        self.c_start_btn = QPushButton("▶ Start CanSat Sim")
        self.c_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.c_start_btn.clicked.connect(self._start_cansat_sim)
        self.c_start_btn.setStyleSheet(self._btn_css(Color.GREEN))
        c_btn_row.addWidget(self.c_start_btn)

        self.c_pause_btn = QPushButton("⏸ Pause")
        self.c_pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.c_pause_btn.clicked.connect(self._pause_cansat_sim)
        self.c_pause_btn.setStyleSheet(self._btn_css(Color.AMBER))
        c_btn_row.addWidget(self.c_pause_btn)

        self.c_stop_btn = QPushButton("■ Stop CanSat Sim")
        self.c_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.c_stop_btn.clicked.connect(self._stop_cansat_sim)
        self.c_stop_btn.setStyleSheet(self._btn_css(Color.RED))
        c_btn_row.addWidget(self.c_stop_btn)
        c_btn_row.addStretch()
        c_lay.addLayout(c_btn_row)
        main_lay.addWidget(c_frame)

        main_lay.addStretch()

    def _btn_css(self, accent_color):
        return f"""
            QPushButton {{
                background-color: {Color.BG_CARD_HOVER};
                color: {Color.TEXT};
                border: 1px solid {accent_color}50;
                border-radius: 4px;
                padding: 8px 16px;
                font: bold 11px 'Menlo';
            }}
            QPushButton:hover {{
                background-color: {accent_color}30;
                border-color: {accent_color};
                color: #fff;
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
            }}
        """

    def _start_both(self):
        self._start_rocket_sim()
        self._start_cansat_sim()

    def _pause_both(self):
        self._pause_rocket_sim()
        self._pause_cansat_sim()

    def _stop_both(self):
        self._stop_rocket_sim()
        self._stop_cansat_sim()

    def _start_rocket_sim(self):
        if self.rocket_running:
            if self.rocket_paused:
                self._pause_rocket_sim() # This will unpause
            return
        from simulator.flight_sim import RocketSimulator
        from ground_station.models import RocketState

        self._r_sim = RocketSimulator()
        self._r_pkt_count = 0
        self.rocket_running = True
        self.rocket_paused = False
        self.r_pause_btn.setText("⏸ Pause")
        self.r_status.setText("● RUNNING")
        self.r_status.setStyleSheet(f"color: {Color.GREEN}; font: bold 11px 'Menlo';")

        _RS = {s.value: s for s in RocketState}

        self._r_timer = QTimer()
        def tick():
            d = self._r_sim.step(0.1)
            self._r_pkt_count += 1
            # Feed into the GUI telemetry pipeline
            self.telem.update_rocket(RocketTelemetry(
                altitude=d["altitude"], velocity=d["velocity"],
                acceleration=d["acceleration"], temperature=d["temperature"],
                pressure=d["pressure"], latitude=d["latitude"],
                longitude=d["longitude"], gps_fix=d["gps_fix"],
                battery=d["battery"], signal=d["signal"],
                roll=d["roll"], pitch=d["pitch"], yaw=d["yaw"],
                state=_RS.get(d["state"], RocketState.BOOT),
            ))
            self.telem.update_elapsed(self._r_sim.t)
            # Also push raw CSV line to COM Monitor terminal
            csv_line = (
                f"SIM,{self._r_sim.t:.2f},{self._r_pkt_count},{d['altitude']},,"
                f"{d['pressure']},{d['temperature']},{d.get('battery',0)/100*4.2:.2f},"
                f"{d['latitude']},{d['longitude']},{d['altitude']},"
                f"{d.get('gps_fix','').split(' ')[-2] if 'satellites' in d.get('gps_fix','') else 8},"
                f"{d['acceleration']},{d.get('roll',0):.2f},{d['state']},OK,OK,0"
            )
            if self.window and hasattr(self.window, "com_monitor_page"):
                self.window.com_monitor_page.r_terminal.append(csv_line)

        self._r_timer.timeout.connect(tick)
        self._r_timer.start(100)  # 10 Hz

    def _pause_rocket_sim(self):
        if not self.rocket_running:
            return
        if self.rocket_paused:
            self.rocket_paused = False
            self.r_pause_btn.setText("⏸ Pause")
            self.r_status.setText("● RUNNING")
            self.r_status.setStyleSheet(f"color: {Color.GREEN}; font: bold 11px 'Menlo';")
            if self._r_timer:
                self._r_timer.start(100)
        else:
            self.rocket_paused = True
            self.r_pause_btn.setText("▶ Resume")
            self.r_status.setText("⏸ PAUSED")
            self.r_status.setStyleSheet(f"color: {Color.AMBER}; font: bold 11px 'Menlo';")
            if self._r_timer:
                self._r_timer.stop()

    def _stop_rocket_sim(self):
        if not self.rocket_running:
            return
        if self._r_timer:
            self._r_timer.stop()
            self._r_timer = None
        self._r_sim = None
        self.rocket_running = False
        self.rocket_paused = False
        self.r_pause_btn.setText("⏸ Pause")
        self.r_status.setText("○ STOPPED")
        self.r_status.setStyleSheet(f"color: {Color.RED}; font: bold 11px 'Menlo';")

    def _start_cansat_sim(self):
        if self.cansat_running:
            if self.cansat_paused:
                self._pause_cansat_sim() # This will unpause
            return
        from simulator.flight_sim import CanSatSimulator
        from ground_station.models import CanSatState

        self._c_sim = CanSatSimulator()
        self._c_pkt_count = 0
        self.cansat_running = True
        self.cansat_paused = False
        self.c_pause_btn.setText("⏸ Pause")
        self.c_status.setText("● RUNNING")
        self.c_status.setStyleSheet(f"color: {Color.GREEN}; font: bold 11px 'Menlo';")

        _CS = {s.value: s for s in CanSatState}

        self._c_timer = QTimer()
        def tick():
            d = self._c_sim.step(0.1)
            self._c_pkt_count += 1
            self.telem.update_cansat(CanSatTelemetry(
                altitude=d["altitude"], velocity=d["velocity"],
                pressure=d["pressure"], temperature=d["temperature"],
                latitude=d["latitude"], longitude=d["longitude"],
                satellite_count=d["satellite_count"], fix_type=d["fix_type"],
                battery=d["battery"], signal=d["signal"],
                roll=d["roll"], pitch=d["pitch"], yaw=d["yaw"],
                state=_CS.get(d["state"], CanSatState.IDLE),
            ))
            self.telem.update_elapsed(self._c_sim.t)
            csv_line = (
                f"SIM,{self._c_sim.t:.2f},{self._c_pkt_count},{d['altitude']},"
                f"{d['pressure']},{d['temperature']},{d.get('battery',0)/100*4.2:.2f},"
                f"{d['latitude']},{d['longitude']},{d['altitude']},"
                f"{d['satellite_count']},{abs(d['velocity']):.2f},"
                f"{d.get('roll',0):.2f},{d['state']}"
            )
            if self.window and hasattr(self.window, "com_monitor_page"):
                self.window.com_monitor_page.c_terminal.append(csv_line)

        self._c_timer.timeout.connect(tick)
        self._c_timer.start(100)  # 10 Hz

    def _pause_cansat_sim(self):
        if not self.cansat_running:
            return
        if self.cansat_paused:
            self.cansat_paused = False
            self.c_pause_btn.setText("⏸ Pause")
            self.c_status.setText("● RUNNING")
            self.c_status.setStyleSheet(f"color: {Color.GREEN}; font: bold 11px 'Menlo';")
            if self._c_timer:
                self._c_timer.start(100)
        else:
            self.cansat_paused = True
            self.c_pause_btn.setText("▶ Resume")
            self.c_status.setText("⏸ PAUSED")
            self.c_status.setStyleSheet(f"color: {Color.AMBER}; font: bold 11px 'Menlo';")
            if self._c_timer:
                self._c_timer.stop()

    def _stop_cansat_sim(self):
        if not self.cansat_running:
            return
        if self._c_timer:
            self._c_timer.stop()
            self._c_timer = None
        self._c_sim = None
        self.cansat_running = False
        self.cansat_paused = False
        self.c_pause_btn.setText("⏸ Pause")
        self.c_status.setText("○ STOPPED")
        self.c_status.setStyleSheet(f"color: {Color.RED}; font: bold 11px 'Menlo';")


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
        self.com_monitor_page = ComMonitorPage(self.telem)
        self.command_console_page = CommandConsolePage(self.telem, window=self)
        self.simulation_page = SimulationPage(self.telem, window=self)

        self.pages.addWidget(self.overview_page)     # pid 0
        self.pages.addWidget(self.rocket_page)        # pid 1
        self.pages.addWidget(self.cansat_page)        # pid 2
        self.pages.addWidget(self.com_monitor_page)   # pid 3
        self.pages.addWidget(self.command_console_page)  # pid 4
        self.pages.addWidget(self.simulation_page)    # pid 5
        content.addWidget(self.pages)

        # Connect Sidebar COM Dropdown
        self.sidebar.com_dropdown.currentTextChanged.connect(self._on_sidebar_com_changed)

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
        # Clear dropdown selection if switching away from COM Monitor
        if pid != 3:
            self.sidebar.com_dropdown.blockSignals(True)
            self.sidebar.com_dropdown.setCurrentIndex(0)
            self.sidebar.com_dropdown.blockSignals(False)

    def _on_sidebar_com_changed(self, text):
        if "Avionics" in text:
            self._on_page(3)
        elif "CanSat" in text:
            self._on_page(3)

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
