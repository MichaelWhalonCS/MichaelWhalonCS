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


_FONT_SM = None
_FONT_MD = None
_FONT_LG = None


def _get_fonts():
    global _FONT_SM, _FONT_MD, _FONT_LG
    if _FONT_SM is None:
        _FONT_SM = _font(14)
        _FONT_MD = _font(18)
        _FONT_LG = _font(26)
    return _FONT_SM, _FONT_MD, _FONT_LG


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _paste_card(canvas: Image.Image, card_img: Image.Image, cx: int, cy: int) -> None:
    x = cx - CARD_W // 2
    y = cy - CARD_H // 2
    canvas.paste(card_img, (x, y), card_img)


def _fmt_pot(pot: float) -> str:
    if pot == int(pot):
        return f"{int(pot):,} BB"
    return f"{pot:g} BB"


# ---------------------------------------------------------------------------
# Chip drawing
# ---------------------------------------------------------------------------

def _chip_color(amount: float) -> tuple[int, int, int]:
    """Return RGB chip color based on BB amount."""
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


def _draw_chip_stack(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                     amount: float, font: ImageFont.ImageFont) -> None:
    """Draw a stack of 3 chips centred at (cx, cy) with the amount below."""
    r = 13
    stack_count = 3
    y_step = 5   # vertical offset per layer (perspective illusion)
    color = _chip_color(amount)
    shadow = (15, 15, 15)
    highlight = tuple(min(255, c + 80) for c in color)

    for i in range(stack_count - 1, -1, -1):
        yo = i * y_step
        # Shadow ellipse (slightly larger, offset down-right)
        draw.ellipse([cx - r + 2, cy - r + yo + 2, cx + r + 2, cy + r + yo + 2],
                     fill=shadow + (160,))
        # Chip body
        draw.ellipse([cx - r, cy - r + yo, cx + r, cy + r + yo],
                     fill=color + (230,), outline=(255, 255, 255, 80), width=1)
        # Inner highlight ring
        draw.ellipse([cx - r + 4, cy - r + yo + 4, cx + r - 4, cy + r + yo - 4],
                     outline=highlight + (120,), width=1)

    # Amount label below the stack
    amt_str = f"{int(amount) if amount == int(amount) else amount:g}"
    bb = draw.textbbox((0, 0), amt_str, font=font)
    tw = bb[2] - bb[0]
    draw.text((cx - tw // 2, cy + r + (stack_count * y_step) + 4),
              amt_str, font=font, fill=(255, 240, 180, 255))


def _chip_pos(player_pos: str) -> tuple[int, int]:
    """
    Return the (x, y) where bet chips should appear for a given position —
    roughly 60 % of the way from the player box toward the table centre.
    """
    px, py = POSITION_COORDS[player_pos]
    cx = int(px * 0.45 + TABLE_CX * 0.55)
    cy = int(py * 0.45 + TABLE_CY * 0.55)
    return cx, cy


# ---------------------------------------------------------------------------
# Player boxes + hole cards helper (shared by build_frame & build_showdown_frame)
# ---------------------------------------------------------------------------

def _draw_players(overlay: Image.Image, hand: HandHistory,
                  folded_positions: set[str],
                  revealed_villain_pos: str | None = None) -> None:
    """Draw all player boxes and hole cards onto overlay (RGBA)."""
    font_sm, _, _ = _get_fonts()
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
            # Empty seat — dimmed placeholder
            ov_draw.rounded_rectangle(
                [bx, by, bx2, by2], radius=6,
                fill=(20, 20, 20, 100), outline=(70, 70, 70, 120), width=1,
            )
            ov_draw.text((bx + 6, by + 4), pos, font=font_sm, fill=(100, 100, 100, 160))
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

    # Hero hole cards — always face-up below the hero box
    if hero_pos and hand.hero_cards and hero_pos in POSITION_COORDS:
        _draw_hole_cards(overlay, hero_pos, hand.hero_cards, face_down=False)

    # Villain hole cards — shown at revealed_villain_pos if set
    if revealed_villain_pos and hand.villain_cards and revealed_villain_pos in POSITION_COORDS:
        _draw_hole_cards(overlay, revealed_villain_pos, hand.villain_cards, face_down=False)


def _draw_hole_cards(overlay: Image.Image, pos: str,
                     cards: list[str], face_down: bool = False) -> None:
    """Paste hole cards below the player box at pos."""
    cx, cy = POSITION_COORDS[pos]
    gap = 6
    total_w = len(cards) * CARD_W + (len(cards) - 1) * gap
    start_x = cx - total_w // 2 + CARD_W // 2
    card_y = cy + PLAYER_BOX_H // 2 + CARD_H // 2 + 4

    for i, cs in enumerate(cards):
        if face_down:
            from renderer.card_sprites import render_card_back
            card_img = render_card_back()
        else:
            rank, suit = normalise_card(cs)
            card_img = render_card(rank, suit)
        _paste_card(overlay, card_img, start_x + i * (CARD_W + gap), card_y)


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
) -> Image.Image:
    font_sm, font_md, font_lg = _get_fonts()

    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), _hex_to_rgb(FELT_COLOR) + (255,))
    draw = ImageDraw.Draw(img)

    # Table oval
    draw.ellipse(TABLE_BBOX, fill=(255, 255, 255, 255), outline=(220, 220, 220, 255), width=4)

    # Pot chips cluster + label
    _draw_pot_chips(draw, pot, font_lg)

    # Community cards
    board = board_so_far if board_so_far is not None else street.board
    if board:
        _draw_board(img, board)

    # Player boxes + hero cards
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    _draw_players(overlay, hand, folded_positions)

    # Bet chips for this action
    if action.amount and action.action in ("bet", "raise", "call", "jam") \
            and action.position in POSITION_COORDS:
        chip_draw = ImageDraw.Draw(overlay)
        cpx, cpy = _chip_pos(action.position)
        _draw_chip_stack(chip_draw, cpx, cpy, action.amount, font_sm)

    img = Image.alpha_composite(img, overlay)

    # Ticker bar
    _draw_ticker(img, action_label, font_md)

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
) -> Image.Image:
    """Special final frame that reveals the villain's hole cards."""
    font_sm, font_md, font_lg = _get_fonts()

    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), _hex_to_rgb(FELT_COLOR) + (255,))
    draw = ImageDraw.Draw(img)

    draw.ellipse(TABLE_BBOX, fill=(255, 255, 255, 255), outline=(220, 220, 220, 255), width=4)
    _draw_pot_chips(draw, pot, font_lg)

    if board_so_far:
        _draw_board(img, board_so_far)

    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    _draw_players(overlay, hand, folded_positions, revealed_villain_pos=villain_pos)
    img = Image.alpha_composite(img, overlay)

    label = "SHOWDOWN" if hand.villain_cards else "HERO WINS"
    _draw_ticker(img, label, font_md)

    return img.convert("RGB")


# ---------------------------------------------------------------------------
# Drawing sub-helpers
# ---------------------------------------------------------------------------

def _draw_pot_chips(draw: ImageDraw.ImageDraw, pot: float,
                    font: ImageFont.ImageFont) -> None:
    """Draw pot label + a small chip cluster just above centre."""
    pot_str = f"Pot: {_fmt_pot(pot)}"
    bb = draw.textbbox((0, 0), pot_str, font=font)
    pw = bb[2] - bb[0]
    # Pot text sits below table centre so it clears the board cards
    pot_text_y = TABLE_CY + 60
    draw.text((TABLE_CX - pw // 2, pot_text_y), pot_str, font=font, fill=POT_TEXT_COLOR)

    # Small chip cluster just above the pot text
    if pot > 0:
        font_sm, _, _ = _get_fonts()
        offsets = [(-18, 0), (0, -5), (18, 0)]
        for dx, dy in offsets:
            _draw_chip_stack(draw, TABLE_CX + dx, pot_text_y - 30 + dy, pot / 3, font_sm)


def _draw_board(img: Image.Image, board: list[str]) -> None:
    card_gap = 8
    total_w = len(board) * CARD_W + (len(board) - 1) * card_gap
    start_x = TABLE_CX - total_w // 2 + CARD_W // 2
    for i, card_str in enumerate(board):
        rank, suit = normalise_card(card_str)
        card_img = render_card(rank, suit)
        _paste_card(img, card_img, start_x + i * (CARD_W + card_gap), BOARD_AREA_Y)


def _draw_ticker(img: Image.Image, label: str,
                 font: ImageFont.ImageFont) -> None:
    ticker = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    td = ImageDraw.Draw(ticker)
    td.rectangle([0, CANVAS_H - TICKER_H, CANVAS_W, CANVAS_H], fill=TICKER_COLOR)
    bb = td.textbbox((0, 0), label, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tx = (CANVAS_W - tw) // 2
    ty = CANVAS_H - TICKER_H + (TICKER_H - th) // 2
    td.text((tx, ty), label, font=font, fill=TICKER_TEXT_COLOR)
    result = Image.alpha_composite(img, ticker)
    img.paste(result)
