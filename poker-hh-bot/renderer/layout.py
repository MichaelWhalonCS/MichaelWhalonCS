CANVAS_W = 1280
CANVAS_H = 720

# ── Colours ──────────────────────────────────────────────────────────────────
BG_COLOR        = (13,  16,  28)      # deep navy canvas
FELT_FILL       = (22,  80,  50)      # rich dark green felt
RAIL_COLOR      = (62,  36,  14)      # dark walnut rail
RAIL_HIGHLIGHT  = (95,  58,  22)      # rail edge highlight
RAIL_INNER_EDGE = (15,  60,  35)      # inner felt shadow

ACTIVE_BOX_COLOR  = (18,  28,  52,  220)   # dark navy player box
FOLDED_BOX_COLOR  = (32,  32,  32,  180)   # greyed-out when folded
GHOST_BOX_COLOR   = (10,  12,  20,   60)   # empty seat, very subtle
GHOST_BOX_BORDER  = (50,  55,  70,   70)

HERO_BORDER_COLOR   = (255, 215,   0)       # gold
NORMAL_BORDER_COLOR = (110, 125, 150)       # muted blue-grey

POT_TEXT_COLOR  = (255, 230,  80)
BOARD_AREA_Y    = 240                       # TABLE_CY(360) - 120

# ── Table geometry ────────────────────────────────────────────────────────────
TABLE_CX = 640
TABLE_CY = 370
TABLE_RX = 390
TABLE_RY = 185

TABLE_BBOX = [
    TABLE_CX - TABLE_RX,
    TABLE_CY - TABLE_RY,
    TABLE_CX + TABLE_RX,
    TABLE_CY + TABLE_RY,
]

RAIL_EXPAND = 22
RAIL_BBOX = [
    TABLE_BBOX[0] - RAIL_EXPAND,
    TABLE_BBOX[1] - RAIL_EXPAND,
    TABLE_BBOX[2] + RAIL_EXPAND,
    TABLE_BBOX[3] + RAIL_EXPAND,
]

# ── Seat positions ────────────────────────────────────────────────────────────
POSITION_COORDS: dict[str, tuple[int, int]] = {
    "BTN":   (1082, 365),
    "CO":    ( 910, 160),
    "HJ":    ( 760, 118),
    "LJ":    ( 640, 115),
    "MP":    ( 520, 118),
    "UTG+1": ( 372, 160),
    "UTG":   ( 220, 278),
    "BB":    ( 148, 400),
    "SB":    ( 235, 538),
}

PLAYER_BOX_W = 108
PLAYER_BOX_H =  54

# ── Ticker ────────────────────────────────────────────────────────────────────
TICKER_H          = 52
TICKER_COLOR      = (8, 10, 20, 220)
TICKER_TEXT_COLOR = (255, 255, 255)
