from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont

from renderer.layout import (
    CANVAS_W, CANVAS_H, FELT_COLOR, TABLE_BBOX,
    POSITION_COORDS, PLAYER_BOX_W, PLAYER_BOX_H,
    HERO_BORDER_COLOR, NORMAL_BORDER_COLOR,
    FOLDED_BOX_COLOR, ACTIVE_BOX_COLOR,
    POT_TEXT_COLOR, BOARD_AREA_Y,
    TICKER_H, TICKER_COLOR, TICKER_TEXT_COLOR,
    TABLE_CX, TABLE_CY,
)
from renderer.card_sprites import render_card, render_card_back, CARD_W, CARD_H
from parser.schema import HandHistory, Street, Action
from bot.utils import normalise_card


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


_FONTS: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size not in _FONTS:
        _FONTS[size] = _font(size)
    return _FONTS[size]


def _get_fonts():
    return _get_font(14), _get_font(18), _get_font(26)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _paste_card(canvas: Image.Image, card_img: Image.Image, cx: int, cy: int) -> None:
    x = cx - CARD_W // 2
    y = cy - CARD_H // 2
    canvas.paste(card_img, (x, y), card_img)


def _fmt_bb(amount: float) -> str:
    return f"{int(amount):g}" if amount == int(amount) else f"{amount:g}"


def _fmt_pot(pot: float) -> str:
    return f"Pot: {_fmt_bb(pot)} BB"


# ---------------------------------------------------------------------------
# Chip drawing
# ---------------------------------------------------------------------------

def _chip_color(amount: float) -> tuple[int, int, int]:
    if amount < 5:
        return (220, 220, 220)   # white
    elif amount < 15:
        return (200, 40, 40)     # red
    elif amount < 40:
        return (50, 160, 60)     # green
    elif amount < 100:
        return (30, 30, 30)      # black
    else:
        return (130, 40, 160)    # purple


def _draw_single_chip_stack(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                             color: tuple[int, int, int], stack: int = 3,
                             r: int = 13, y_step: int = 5) -> None:
    """Draw a stack of chips at (cx, cy) — no label."""
    shadow = (15, 15, 15)
    highlight = tuple(min(255, c + 80) for c in color)
    for i in range(stack - 1, -1, -1):
        yo = i * y_step
        draw.ellipse([cx - r + 2, cy - r + yo + 2, cx + r + 2, cy + r + yo + 2],
                     fill=shadow + (160,))
        draw.ellipse([cx - r, cy - r + yo, cx + r, cy + r + yo],
                     fill=color + (230,), outline=(255, 255, 255, 60), width=1)
        draw.ellipse([cx - r + 4, cy - r + yo + 4, cx + r - 4, cy + r + yo - 4],
                     outline=highlight + (100,), width=1)


def _draw_bet_chips(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    amount: float) -> None:
    """Draw chips + amount label for a player bet."""
    font = _get_font(13)
    color = _chip_color(amount)
    r, stack, y_step = 13, 3, 5
    _draw_single_chip_stack(draw, cx, cy, color, stack, r, y_step)
    # Amount label below stack, offset clear of chips
    label = _fmt_bb(amount)
    bb = draw.textbbox((0, 0), label, font=font)
    tw = bb[2] - bb[0]
    label_y = cy + r + stack * y_step + 5
    # Dark bg behind label for legibility
    draw.rectangle([cx - tw // 2 - 2, label_y - 1,
                    cx + tw // 2 + 2, label_y + (bb[3] - bb[1]) + 1],
                   fill=(0, 0, 0, 160))
    draw.text((cx - tw // 2, label_y), label, font=font, fill=(255, 240, 180, 255))


def _chip_pos(pos: str) -> tuple[int, int]:
    """Position for bet chips — 65% toward player, 35% toward table centre."""
    px, py = POSITION_COORDS[pos]
    cx = int(px * 0.65 + TABLE_CX * 0.35)
    cy = int(py * 0.65 + TABLE_CY * 0.35)
    return cx, cy


# ---------------------------------------------------------------------------
# Action log (top-right corner)
# ---------------------------------------------------------------------------

def _draw_action_log(img: Image.Image, history: list[str]) -> None:
    """
    Draw a semi-transparent action history panel in the top-right corner.
    Street headers are blue, past actions are grey, current action is gold.
    """
    if not history:
        return

    font = _get_font(14)
    pad = 10
    line_h = 19
    panel_w = 290
    max_lines = 14

    lines = history[-max_lines:]
    panel_h = len(lines) * line_h + pad * 2

    x = CANVAS_W - panel_w - pad
    y = pad

    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    d.rounded_rectangle([x, y, x + panel_w, y + panel_h],
                        radius=6, fill=(8, 8, 8, 185))

    for i, line in enumerate(lines):
        ly = y + pad + i * line_h
        is_current = (i == len(lines) - 1)
        is_header = line.startswith("▸")

        if is_header:
            color = (140, 180, 255, 255)   # blue street header
        elif is_current:
            color = (255, 215, 0, 255)     # gold current action
        else:
            color = (190, 190, 190, 210)   # grey past actions

        d.text((x + pad, ly), line, font=font, fill=color)

    result = Image.alpha_composite(img, overlay)
    img.paste(result)


# ---------------------------------------------------------------------------
# Player boxes + hole cards helper
# ---------------------------------------------------------------------------

def _draw_players(overlay: Image.Image, hand: HandHistory,
                  folded_positions: set[str],
                  revealed_villain_pos: str | None = None) -> None:
    font_sm = _get_font(14)
    ov_draw = ImageDraw.Draw(overlay)

    player_map = {p.position: p for p in hand.players}
    hero_pos = next((p.position for p in hand.players if p.is_hero), None)
    active_positions = {p.position for p in hand.players}

    for pos, (cx, cy) in POSITION_COORDS.items():
        bx = cx - PLAYER_BOX_W // 2
        by = cy - PLAYER_BOX_H // 2
        bx2 = bx + PLAYER_BOX_W
        by2 = by + PLAYER_BOX_H

        is_hero = pos == hero_pos
        is_folded = pos in folded_positions
        player = player_map.get(pos)

        if player is None and pos not in active_positions:
            ov_draw.rounded_rectangle(
                [bx, by, bx2, by2], radius=6,
                fill=(20, 20, 20, 100), outline=(70, 70, 70, 120), width=1,
            )
            ov_draw.text((bx + 6, by + 4), pos, font=font_sm,
                         fill=(100, 100, 100, 160))
            continue

        box_fill = FOLDED_BOX_COLOR if is_folded else ACTIVE_BOX_COLOR
        border_color = HERO_BORDER_COLOR + (255,) if is_hero else NORMAL_BORDER_COLOR + (255,)
        border_w = 3 if is_hero else 1

        ov_draw.rounded_rectangle(
            [bx, by, bx2, by2], radius=6,
            fill=box_fill, outline=border_color, width=border_w,
        )

        label = pos
        if player and player.stack is not None:
            label = f"{pos}\n{int(player.stack)} BB"
        if is_folded:
            label = f"{pos}\nFOLDED"

        text_color = (200, 200, 200, 200) if is_folded else (255, 255, 255, 255)
        ov_draw.text((bx + 6, by + 4), label, font=font_sm, fill=text_color)

    # Hero hole cards (hero-perspective hands)
    if hero_pos and hand.hero_cards and hero_pos in POSITION_COORDS:
        _draw_hole_cards(overlay, hero_pos, hand.hero_cards, face_down=False)

    # Villain hole cards at showdown (hero-perspective hands)
    if revealed_villain_pos and hand.villain_cards and revealed_villain_pos in POSITION_COORDS:
        _draw_hole_cards(overlay, revealed_villain_pos, hand.villain_cards, face_down=False)

    # No-hero case: draw hole cards stored on each player object
    if not hero_pos:
        for p in hand.players:
            if p.hole_cards and p.position in POSITION_COORDS:
                _draw_hole_cards(overlay, p.position, p.hole_cards, face_down=False)


def _draw_hole_cards(overlay: Image.Image, pos: str,
                     cards: list[str], face_down: bool = False) -> None:
    from renderer.layout import PLAYER_BOX_W
    cx, cy = POSITION_COORDS[pos]
    n = len(cards)
    # For PLO (4 cards) tighten the gap so they all fit near the player box
    max_w = max(PLAYER_BOX_W, CARD_W * n + 4)
    gap = max(2, (max_w - CARD_W * n) // max(n - 1, 1)) if n > 1 else 6
    gap = min(gap, 8)
    total_w = n * CARD_W + (n - 1) * gap
    start_x = cx - total_w // 2 + CARD_W // 2
    card_y = cy + PLAYER_BOX_H // 2 + CARD_H // 2 + 4

    for i, cs in enumerate(cards):
        if face_down:
            card_img = render_card_back()
        else:
            rank, suit = normalise_card(cs)
            card_img = render_card(rank, suit)
        _paste_card(overlay, card_img, start_x + i * (CARD_W + gap), card_y)


# ---------------------------------------------------------------------------
# Sub-helpers shared by build_frame & build_showdown_frame
# ---------------------------------------------------------------------------

def _draw_pot(draw: ImageDraw.ImageDraw, pot: float) -> None:
    """Pot chip cluster + label, positioned below the board cards."""
    font_lg = _get_font(26)
    font_sm = _get_font(14)

    pot_text_y = TABLE_CY + 55
    pot_str = _fmt_pot(pot)
    bb = draw.textbbox((0, 0), pot_str, font=font_lg)
    pw = bb[2] - bb[0]
    draw.text((TABLE_CX - pw // 2, pot_text_y), pot_str, font=font_lg,
              fill=POT_TEXT_COLOR)

    # 3-chip decorative cluster just above the text — no per-chip labels
    if pot > 0:
        chip_y = pot_text_y - 28
        color = _chip_color(pot)
        offsets = [(-20, 2), (0, -4), (20, 2)]
        for dx, dy in offsets:
            _draw_single_chip_stack(draw, TABLE_CX + dx, chip_y + dy,
                                    color, stack=2, r=11, y_step=4)


def _draw_board(img: Image.Image, board: list[str]) -> None:
    card_gap = 8
    total_w = len(board) * CARD_W + (len(board) - 1) * card_gap
    start_x = TABLE_CX - total_w // 2 + CARD_W // 2
    for i, card_str in enumerate(board):
        rank, suit = normalise_card(card_str)
        _paste_card(img, render_card(rank, suit),
                    start_x + i * (CARD_W + card_gap), BOARD_AREA_Y)


def _draw_ticker(img: Image.Image, label: str) -> None:
    font_md = _get_font(18)
    ticker = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    td = ImageDraw.Draw(ticker)
    td.rectangle([0, CANVAS_H - TICKER_H, CANVAS_W, CANVAS_H], fill=TICKER_COLOR)
    bb = td.textbbox((0, 0), label, font=font_md)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    td.text(((CANVAS_W - tw) // 2, CANVAS_H - TICKER_H + (TICKER_H - th) // 2),
            label, font=font_md, fill=TICKER_TEXT_COLOR)
    result = Image.alpha_composite(img, ticker)
    img.paste(result)


# ---------------------------------------------------------------------------
# Main frame builder
# ---------------------------------------------------------------------------

def build_frame(
    hand: HandHistory,
    street: Street,
    action: Action,
    pot: float,
    folded_positions: set[str],
    action_label: str,
    board_so_far: list[str] | None = None,
    action_history: list[str] | None = None,
) -> Image.Image:
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), _hex_to_rgb(FELT_COLOR) + (255,))
    draw = ImageDraw.Draw(img)

    # Table oval
    draw.ellipse(TABLE_BBOX, fill=(255, 255, 255, 255),
                 outline=(220, 220, 220, 255), width=4)

    # Community cards
    board = board_so_far if board_so_far is not None else street.board
    if board:
        _draw_board(img, board)

    # Pot (drawn after board so text sits below)
    _draw_pot(draw, pot)

    # Player boxes + hole cards
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    _draw_players(overlay, hand, folded_positions)

    # Bet chips for this action
    if action.amount and action.action in ("bet", "raise", "call", "jam") \
            and action.position in POSITION_COORDS:
        chip_draw = ImageDraw.Draw(overlay)
        cpx, cpy = _chip_pos(action.position)
        _draw_bet_chips(chip_draw, cpx, cpy, action.amount)

    img = Image.alpha_composite(img, overlay)

    # Action log panel (top-right)
    if action_history:
        _draw_action_log(img, action_history)

    # Bottom ticker
    _draw_ticker(img, action_label)

    return img.convert("RGB")


# ---------------------------------------------------------------------------
# Showdown frame
# ---------------------------------------------------------------------------

def build_showdown_frame(
    hand: HandHistory,
    board_so_far: list[str],
    pot: float,
    folded_positions: set[str],
    villain_pos: str | None,
    action_history: list[str] | None = None,
) -> Image.Image:
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), _hex_to_rgb(FELT_COLOR) + (255,))
    draw = ImageDraw.Draw(img)

    draw.ellipse(TABLE_BBOX, fill=(255, 255, 255, 255),
                 outline=(220, 220, 220, 255), width=4)

    if board_so_far:
        _draw_board(img, board_so_far)

    _draw_pot(draw, pot)

    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    _draw_players(overlay, hand, folded_positions, revealed_villain_pos=villain_pos)
    img = Image.alpha_composite(img, overlay)

    if action_history:
        log = action_history + ["▸ SHOWDOWN"]
        _draw_action_log(img, log)

    has_hero = any(p.is_hero for p in hand.players)
    if not has_hero:
        label = hand.result or "SHOWDOWN"
    elif hand.villain_cards:
        label = "SHOWDOWN"
    else:
        label = "HERO WINS"
    _draw_ticker(img, label)

    return img.convert("RGB")
