"""
Hardcoded canvas dimensions, table geometry, and player-position coordinates.

Canvas: 1280 × 720 (HD landscape)
Table:  white oval centred at (640, 360)
        horizontal radius 390 px, vertical radius 185 px

The seven standard positions are distributed around the oval perimeter
in clockwise order starting from the right (dealer/BTN side):

         HJ
    UTG+1    CO
  UTG          BTN
    BB
      SB

Pixel coordinates are (cx, cy) for the centre of each player label box.
All coordinates were chosen so the boxes stay fully inside the 1280×720
canvas while sitting visually just outside the table oval.
"""

# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------
CANVAS_W = 1280
CANVAS_H = 720

FELT_COLOR = "#35654d"          # casino felt green

# ---------------------------------------------------------------------------
# Table oval
# ---------------------------------------------------------------------------
TABLE_CX = 640
TABLE_CY = 360
TABLE_RX = 390                  # horizontal radius
TABLE_RY = 185                  # vertical radius

# Bounding box for ImageDraw.ellipse
TABLE_BBOX = [
    TABLE_CX - TABLE_RX,
    TABLE_CY - TABLE_RY,
    TABLE_CX + TABLE_RX,
    TABLE_CY + TABLE_RY,
]

# ---------------------------------------------------------------------------
# Player position coordinates
# (cx, cy) — centre of the 100 × 54 player label box
#
# Arrangement (clockwise from right):
#
#       HJ (640, 112)
#   UTG+1 (400, 148)      CO (880, 148)
# UTG (238, 255)                BTN (1082, 355)
#   BB (158, 390)
#     SB (255, 528)
# ---------------------------------------------------------------------------
POSITION_COORDS: dict[str, tuple[int, int]] = {
    "BTN":   (1082, 355),
    "CO":    (910,  155),
    "HJ":    (640,  112),
    "UTG+1": (372,  155),
    "UTG":   (220,  270),
    "BB":    (148,  390),
    "SB":    (235,  528),
}

# Player box dimensions
PLAYER_BOX_W = 100
PLAYER_BOX_H = 52

# ---------------------------------------------------------------------------
# Colours / style constants
# ---------------------------------------------------------------------------
HERO_BORDER_COLOR = (255, 215, 0)       # gold
NORMAL_BORDER_COLOR = (180, 180, 180)   # light grey
FOLDED_BOX_COLOR = (60, 60, 60, 180)    # dark, semi-transparent
ACTIVE_BOX_COLOR = (30, 30, 50, 200)    # dark navy, semi-transparent

POT_TEXT_COLOR = (255, 230, 0)          # bright yellow
BOARD_AREA_Y = TABLE_CY - 30            # vertical centre for board cards

TICKER_H = 48                           # height of the bottom action bar
TICKER_COLOR = (10, 10, 10, 190)        # near-black, semi-transparent
TICKER_TEXT_COLOR = (255, 255, 255)
