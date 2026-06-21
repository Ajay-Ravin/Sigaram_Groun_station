"""
Professional Aerospace Widgets
Gauges · Attitude Indicators · Telemetry Cards · Event Log
"""
import math
from typing import List, Dict, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRect, QRectF, QPointF, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QConicalGradient,
    QRadialGradient, QLinearGradient, QPainterPath, QFontMetrics,
)
import pyqtgraph as pg

from ground_station.theme import Color, Style


# ═══════════════════════════════════════════════════════════════════
#  AEROSPACE GAUGE — full circular with tick marks & warning zones
# ═══════════════════════════════════════════════════════════════════

class AeroGauge(QWidget):
    """
    270-degree sweep gauge with major/minor ticks, numeric labels,
    colour warning zones, digital readout, and smooth needle.
    """

    def __init__(
        self,
        title: str,
        unit: str,
        min_val: float,
        max_val: float,
        major_step: float,
        minor_divisions: int = 5,
        warn_start: Optional[float] = None,
        danger_start: Optional[float] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.major_step = major_step
        self.minor_divisions = minor_divisions
        self.warn_start = warn_start
        self.danger_start = danger_start

        self._value = min_val
        self._display_value = min_val  # for animation

        self.setMinimumSize(170, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(Style.GLASSMORPHISM_PANEL)

    # --- public API ---
    def set_value(self, v: float):
        self._value = max(self.min_val, min(self.max_val, v))
        # Smooth animation: lerp toward target
        self._display_value += (self._value - self._display_value) * 0.35
        self.update()

    # --- helpers ---
    def _val_to_angle(self, v: float) -> float:
        """Map value → angle in degrees. Sweep is 270°, starting at 225° (7-o'clock)."""
        frac = (v - self.min_val) / (self.max_val - self.min_val) if self.max_val != self.min_val else 0
        frac = max(0.0, min(1.0, frac))
        return 225.0 - frac * 270.0  # clockwise

    def _zone_color(self, v: float) -> QColor:
        if self.danger_start is not None and v >= self.danger_start:
            return QColor(Color.GAUGE_DANGER)
        if self.warn_start is not None and v >= self.warn_start:
            return QColor(Color.GAUGE_WARN)
        return QColor(Color.GAUGE_NORMAL)

    # --- paint ---
    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2 + 4
            radius = min(w, h) / 2 - 18

            # --- background ring ---
            pen = QPen(QColor(Color.GAUGE_BG), 10)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            p.drawArc(arc_rect, int(-45 * 16), int(270 * 16))

            # --- colored value arc ---
            zone_col = self._zone_color(self._display_value)
            zone_col_dim = QColor(zone_col)
            zone_col_dim.setAlpha(180)
            pen2 = QPen(zone_col_dim, 6)
            pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen2)
            frac = (self._display_value - self.min_val) / (self.max_val - self.min_val) if self.max_val != self.min_val else 0
            frac = max(0.0, min(1.0, frac))
            sweep = frac * 270.0
            p.drawArc(arc_rect, int(225 * 16), int(-sweep * 16))

            # --- tick marks ---
            num_major = int((self.max_val - self.min_val) / self.major_step) if self.major_step > 0 else 1
            for i in range(num_major + 1):
                val = self.min_val + i * self.major_step
                ang = math.radians(self._val_to_angle(val))
                # major tick
                inner = radius - 14
                outer = radius - 4
                x1 = cx + inner * math.cos(ang)
                y1 = cy - inner * math.sin(ang)
                x2 = cx + outer * math.cos(ang)
                y2 = cy - outer * math.sin(ang)
                p.setPen(QPen(QColor(Color.GAUGE_TICK_MAJOR), 1.5))
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

                # label
                label_r = radius - 22
                lx = cx + label_r * math.cos(ang)
                ly = cy - label_r * math.sin(ang)
                font = QFont("Menlo", 7)
                p.setFont(font)
                p.setPen(QPen(QColor(Color.TEXT_DIM)))
                txt = f"{val:g}"
                fm = QFontMetrics(font)
                tw = fm.horizontalAdvance(txt)
                p.drawText(QPointF(lx - tw / 2, ly + 4), txt)

                # minor ticks
                if i < num_major:
                    for j in range(1, self.minor_divisions):
                        mv = val + j * self.major_step / self.minor_divisions
                        ma = math.radians(self._val_to_angle(mv))
                        mi = radius - 10
                        mo = radius - 4
                        p.setPen(QPen(QColor(Color.GAUGE_TICK), 0.8))
                        p.drawLine(
                            QPointF(cx + mi * math.cos(ma), cy - mi * math.sin(ma)),
                            QPointF(cx + mo * math.cos(ma), cy - mo * math.sin(ma)),
                        )

            # --- warning zone arc ---
            if self.warn_start is not None:
                self._draw_zone_arc(p, arc_rect, self.warn_start,
                                    self.danger_start if self.danger_start else self.max_val,
                                    QColor(Color.GAUGE_WARN), 40)
            if self.danger_start is not None:
                self._draw_zone_arc(p, arc_rect, self.danger_start, self.max_val,
                                    QColor(Color.GAUGE_DANGER), 50)

            # --- needle ---
            needle_ang = math.radians(self._val_to_angle(self._display_value))
            nx = cx + (radius - 8) * math.cos(needle_ang)
            ny = cy - (radius - 8) * math.sin(needle_ang)
            # glow
            glow = QPen(zone_col, 4)
            gc = QColor(zone_col)
            gc.setAlpha(60)
            glow.setColor(gc)
            glow.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(glow)
            p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
            # main
            p.setPen(QPen(zone_col, 2, cap=Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
            # center dot
            p.setBrush(QBrush(zone_col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), 4, 4)
            p.setBrush(QBrush(QColor(Color.BG_PRIMARY)))
            p.drawEllipse(QPointF(cx, cy), 2, 2)

            # --- digital readout ---
            p.setFont(QFont("Menlo", 13, QFont.Weight.Bold))
            p.setPen(QPen(zone_col))
            val_txt = f"{self._display_value:.1f}"
            p.drawText(QRectF(0, cy + radius * 0.25, w, 22),
                       Qt.AlignmentFlag.AlignCenter, val_txt)
            # unit
            p.setFont(QFont("Menlo", 8))
            p.setPen(QPen(QColor(Color.TEXT_DIM)))
            p.drawText(QRectF(0, cy + radius * 0.25 + 18, w, 14),
                       Qt.AlignmentFlag.AlignCenter, self.unit)
            # title
            p.setFont(QFont("Menlo", 8, QFont.Weight.Bold))
            p.setPen(QPen(QColor(Color.CYAN)))
            p.drawText(QRectF(0, 6, w, 14), Qt.AlignmentFlag.AlignCenter, self.title)

            p.end()
        except Exception as e:
            print(f"[GAUGE ERROR] {e}")

    def _draw_zone_arc(self, p: QPainter, rect: QRectF,
                       start_val: float, end_val: float, color: QColor, alpha: int):
        c = QColor(color)
        c.setAlpha(alpha)
        pen = QPen(c, 10)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        a1 = self._val_to_angle(start_val)
        a2 = self._val_to_angle(end_val)
        p.drawArc(rect, int(a1 * 16), int((a2 - a1) * 16))


# ═══════════════════════════════════════════════════════════════════
#  ATTITUDE INDICATOR — artificial horizon
# ═══════════════════════════════════════════════════════════════════

class AttitudeIndicator(QWidget):
    """Artificial-horizon style attitude display showing roll, pitch, yaw."""

    def __init__(self, title: str = "ATTITUDE", parent=None):
        super().__init__(parent)
        self.title = title
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self.setMinimumSize(180, 210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(Style.GLASSMORPHISM_PANEL)

    def set_attitude(self, roll: float, pitch: float, yaw: float):
        self._roll = roll
        self._pitch = pitch
        self._yaw = yaw
        self.update()

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            # title
            p.setFont(QFont("Menlo", 8, QFont.Weight.Bold))
            p.setPen(QPen(QColor(Color.CYAN)))
            p.drawText(QRectF(0, 4, w, 14), Qt.AlignmentFlag.AlignCenter, self.title)

            # Horizon circle
            cx, cy = w / 2, h / 2 - 2
            r = min(w, h) / 2 - 24

            # Clip to circle
            path = QPainterPath()
            path.addEllipse(QPointF(cx, cy), r, r)
            p.setClipPath(path)

            # Sky / ground split based on pitch
            p.save()
            p.translate(cx, cy)
            p.rotate(-self._roll)

            pitch_px = self._pitch * r / 45.0  # 45° fills half

            # Sky
            p.fillRect(QRectF(-r * 2, -r * 2, r * 4, r * 2 + pitch_px),
                        QBrush(QColor("#0A2040")))
            # Ground
            p.fillRect(QRectF(-r * 2, pitch_px, r * 4, r * 4),
                        QBrush(QColor("#3A2010")))

            # Horizon line
            p.setPen(QPen(QColor("#FFFFFF"), 1.5))
            p.drawLine(QPointF(-r * 2, pitch_px), QPointF(r * 2, pitch_px))

            # Pitch ladder
            p.setPen(QPen(QColor("#FFFFFF80"), 0.8))
            p.setFont(QFont("Menlo", 6))
            for deg in range(-30, 31, 10):
                if deg == 0:
                    continue
                yy = pitch_px - deg * r / 45.0
                half = r * 0.3 if deg % 20 == 0 else r * 0.15
                p.drawLine(QPointF(-half, yy), QPointF(half, yy))
                if deg % 20 == 0:
                    p.drawText(QPointF(half + 3, yy + 3), f"{deg}")

            p.restore()
            p.setClipping(False)

            # Circle border
            p.setPen(QPen(QColor(Color.BORDER), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)

            # Fixed aircraft reference
            p.setPen(QPen(QColor(Color.AMBER), 2.5))
            p.drawLine(QPointF(cx - r * 0.35, cy), QPointF(cx - r * 0.1, cy))
            p.drawLine(QPointF(cx + r * 0.1, cy), QPointF(cx + r * 0.35, cy))
            p.drawLine(QPointF(cx, cy - r * 0.1), QPointF(cx, cy + r * 0.05))

            # Roll indicator triangle at top
            p.save()
            p.translate(cx, cy)
            p.rotate(-self._roll)
            tri = QPainterPath()
            tri.moveTo(0, -r + 2)
            tri.lineTo(-5, -r + 10)
            tri.lineTo(5, -r + 10)
            tri.closeSubpath()
            p.fillPath(tri, QBrush(QColor(Color.AMBER)))
            p.restore()

            # Digital readout below
            y_text = cy + r + 6
            p.setFont(QFont("Menlo", 8))
            p.setPen(QPen(QColor(Color.TEXT)))
            readout = f"R {self._roll:+.1f}°  P {self._pitch:+.1f}°  Y {self._yaw:+.1f}°"
            p.drawText(QRectF(0, y_text, w, 14), Qt.AlignmentFlag.AlignCenter, readout)

            p.end()
        except Exception as e:
            print(f"[ATTITUDE ERROR] {e}")


# ═══════════════════════════════════════════════════════════════════
#  TELEMETRY CARD — key-value readout panel
# ═══════════════════════════════════════════════════════════════════

class TelemetryCard(QFrame):
    """Compact key-value telemetry card."""

    def __init__(self, title: str, fields: List[str], parent=None):
        super().__init__(parent)
        self.setStyleSheet(Style.GLASSMORPHISM_PANEL)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        lbl = QLabel(title)
        lbl.setStyleSheet(Style.LABEL_TITLE)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {Color.BORDER};")
        layout.addWidget(sep)

        self._labels: Dict[str, QLabel] = {}
        for f in fields:
            row = QHBoxLayout()
            row.setSpacing(4)
            key = QLabel(f)
            key.setStyleSheet(Style.LABEL_DIM)
            key.setFixedWidth(100)
            val = QLabel("—")
            val.setStyleSheet(Style.LABEL_VALUE)
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(key)
            row.addWidget(val)
            layout.addLayout(row)
            self._labels[f] = val

    def set_field(self, key: str, value: str, color: Optional[str] = None):
        if key in self._labels:
            self._labels[key].setText(value)
            if color:
                self._labels[key].setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")


# ═══════════════════════════════════════════════════════════════════
#  MISSION EVENT LOG
# ═══════════════════════════════════════════════════════════════════

class EventLogWidget(QFrame):
    """Vertical mission event timeline — newest at top."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(Style.GLASSMORPHISM_PANEL)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(8, 6, 8, 6)
        self.outer.setSpacing(4)

        title = QLabel("MISSION EVENTS")
        title.setStyleSheet(Style.LABEL_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.outer.addWidget(title)

    def add_event(self, ev):
        mins = int(ev.time) // 60
        secs = int(ev.time) % 60
        lbl = QLabel(f"T+{mins:02d}:{secs:02d}  {ev.label}")
        lbl.setStyleSheet(f"color: {ev.color}; font-size: 10px; font-family: Menlo;")
        lbl.setWordWrap(True)
        # Insert below the title (index 1)
        self.outer.insertWidget(1, lbl)
        self.updateGeometry()


# ═══════════════════════════════════════════════════════════════════
#  STATE BAR
# ═══════════════════════════════════════════════════════════════════

class StateBar(QWidget):
    """Horizontal mission phase indicator."""

    def __init__(self, states: List[str], accent: str, parent=None):
        super().__init__(parent)
        self.states = states
        self.accent = accent
        self.current_idx = 0
        self.setFixedHeight(32)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background: {Color.BG_CARD}; border-radius: 4px;")

    def set_state(self, name: str):
        if name in self.states:
            self.current_idx = self.states.index(name)
            self.update()

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            sw = w / len(self.states)
            for i, s in enumerate(self.states):
                x = i * sw
                if i == self.current_idx:
                    col = QColor(self.accent)
                    col.setAlpha(200)
                    p.fillRect(QRectF(x + 1, 1, sw - 2, h - 2), QBrush(col))
                    p.setPen(QPen(QColor("#FFFFFF")))
                elif i < self.current_idx:
                    past = QColor(self.accent)
                    past.setAlpha(40)
                    p.fillRect(QRectF(x + 1, 1, sw - 2, h - 2), QBrush(past))
                    p.setPen(QPen(QColor(Color.TEXT_DIM)))
                else:
                    p.setPen(QPen(QColor(Color.TEXT_MUTED)))
                p.setFont(QFont("Menlo", 8, QFont.Weight.Bold))
                p.drawText(QRectF(x, 0, sw, h), Qt.AlignmentFlag.AlignCenter, s)
            p.end()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
#  LIVE GRAPH — pyqtgraph wrapper with auto-scale & scrolling
# ═══════════════════════════════════════════════════════════════════

class LiveGraph(QWidget):
    """Auto-scaling, scrolling telemetry plot (10 min history)."""

    MAX_POINTS = 6000  # 10 min at 10 Hz

    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setMaximumHeight(160)
        self.setStyleSheet(Style.GLASSMORPHISM_PANEL)
        self._data: List[float] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(QColor(Color.BG_CARD))
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.setTitle(title, color=Color.CYAN, size="9pt")
        self.plot_widget.getAxis('left').setPen(pg.mkPen(Color.TEXT_DIM))
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen(Color.TEXT_DIM))
        self.plot_widget.getAxis('left').setTextPen(pg.mkPen(Color.TEXT_DIM))
        self.plot_widget.getAxis('bottom').setTextPen(pg.mkPen(Color.TEXT_DIM))
        self.plot_widget.enableAutoRange(axis='y')

        self._line = self.plot_widget.plot(
            pen=pg.mkPen(color=color, width=2),
        )
        layout.addWidget(self.plot_widget)

    def add_point(self, v: float):
        self._data.append(v)
        if len(self._data) > self.MAX_POINTS:
            self._data.pop(0)
        self._line.setData(self._data)


# ═══════════════════════════════════════════════════════════════════
#  STATUS HEADER BAR
# ═══════════════════════════════════════════════════════════════════

class StatusHeader(QWidget):
    """Top bar: mission status, timer, GPS, link quality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {Color.BG_PANEL}, stop:1 {Color.BG_PRIMARY});
                border-bottom: 1px solid {Color.CYAN}40;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(24)

        self._mission = self._make("MISSION", "PRE-FLIGHT", Color.AMBER)
        self._timer = self._make("T+", "00:00", Color.CYAN)
        self._gps = self._make("GPS", "NO FIX", Color.TEXT_DIM)
        self._link = self._make("LINK", "—", Color.TEXT_DIM)
        self._rbat = self._make("R-BAT", "—", Color.GREEN)
        self._cbat = self._make("C-BAT", "—", Color.GREEN)

        for w in [self._mission, self._timer, self._gps, self._link, self._rbat, self._cbat]:
            lay.addWidget(w)
        lay.addStretch()

    def _make(self, key: str, val: str, color: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 4, 0, 4)
        l.setSpacing(0)
        k = QLabel(key)
        k.setStyleSheet(f"color: {Color.TEXT_DIM}; font: bold 8px 'Menlo';")
        k.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v = QLabel(val)
        v.setStyleSheet(f"color: {color}; font: bold 13px 'Menlo';")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(k)
        l.addWidget(v)
        w._val_label = v
        return w

    def update_header(self, rocket, cansat, elapsed):
        m, s = int(elapsed) // 60, int(elapsed) % 60
        self._timer._val_label.setText(f"{m:02d}:{s:02d}")

        state = rocket.state.value
        state_colors = {
            "Boot": Color.TEXT_DIM,
            "Pre_launch": Color.AMBER,
            "ascent": Color.RED,
            "Deployment": Color.CYAN,
            "Descent": Color.BLUE,
            "Impact/recovery": Color.GREEN
        }
        col = state_colors.get(state, Color.AMBER)
        self._mission._val_label.setText(state)
        self._mission._val_label.setStyleSheet(f"color: {col}; font: bold 13px 'Menlo';")

        self._gps._val_label.setText(f"{rocket.gps_fix[:2]}")
        gps_col = Color.GREEN if "3D" in rocket.gps_fix else Color.AMBER
        self._gps._val_label.setStyleSheet(f"color: {gps_col}; font: bold 13px 'Menlo';")

        sig = max(rocket.signal, cansat.signal)
        link_col = Color.GREEN if sig > -80 else (Color.AMBER if sig > -100 else Color.RED)
        self._link._val_label.setText(f"{sig} dBm")
        self._link._val_label.setStyleSheet(f"color: {link_col}; font: bold 13px 'Menlo';")

        def bat_col(b):
            return Color.GREEN if b > 50 else (Color.AMBER if b > 20 else Color.RED)
        self._rbat._val_label.setText(f"{rocket.battery}%")
        self._rbat._val_label.setStyleSheet(f"color: {bat_col(rocket.battery)}; font: bold 13px 'Menlo';")
        self._cbat._val_label.setText(f"{cansat.battery}%")
        self._cbat._val_label.setStyleSheet(f"color: {bat_col(cansat.battery)}; font: bold 13px 'Menlo';")
