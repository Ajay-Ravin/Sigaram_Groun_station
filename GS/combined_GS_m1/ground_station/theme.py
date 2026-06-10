"""
Aerospace Mission Control Theme — Colors, Fonts, Styles
"""


class Color:
    """NASA/SpaceX-inspired dark aerospace palette"""
    # Backgrounds
    BG_PRIMARY = "#080E1A"
    BG_PANEL = "#0C1526"
    BG_CARD = "#101D30"
    BG_CARD_HOVER = "#152640"
    BG_INPUT = "#0A1220"

    # Accent
    CYAN = "#00D4FF"
    CYAN_DIM = "#007A99"
    CYAN_GLOW = "#00D4FF40"
    GREEN = "#00FF88"
    GREEN_DIM = "#00994D"
    AMBER = "#FFB800"
    AMBER_DIM = "#996E00"
    RED = "#FF3344"
    RED_DIM = "#991F29"
    BLUE = "#3388FF"

    # Text
    TEXT = "#E0F0FF"
    TEXT_DIM = "#6088AA"
    TEXT_MUTED = "#304560"

    # Borders
    BORDER = "#1A2E44"
    BORDER_GLOW = "#00D4FF44"

    # Gauge zones
    GAUGE_NORMAL = "#00FF88"
    GAUGE_WARN = "#FFB800"
    GAUGE_DANGER = "#FF3344"
    GAUGE_BG = "#162030"
    GAUGE_TICK = "#405060"
    GAUGE_TICK_MAJOR = "#8090A0"


class Style:
    """Reusable stylesheet fragments"""

    GLASSMORPHISM_PANEL = f"""
        background-color: rgba(12, 21, 38, 0.85);
        border: 1px solid {Color.BORDER};
        border-radius: 8px;
    """

    CARD = f"""
        background-color: {Color.BG_CARD};
        border: 1px solid {Color.BORDER};
        border-radius: 6px;
        padding: 8px;
    """

    LABEL_TITLE = f"color: {Color.CYAN}; font-size: 11px; font-weight: bold;"
    LABEL_VALUE = f"color: {Color.TEXT}; font-size: 13px; font-weight: bold;"
    LABEL_UNIT = f"color: {Color.TEXT_DIM}; font-size: 9px;"
    LABEL_DIM = f"color: {Color.TEXT_DIM}; font-size: 10px;"
