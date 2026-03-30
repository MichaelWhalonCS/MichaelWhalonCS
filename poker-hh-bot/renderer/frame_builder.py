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
from renderer.card_sprites import render_card, render_card_back, render_cards, CARD_W, CARD_H
from parser.schema import HandHistory, Street, Action
from bot.utils import normalise_card


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


def build_frame(
    hand: HandHistory,
    street: Street,
    action: Action,
    pot: float,
    folded_positions: set[str],
    action_label: str,
    board_so_far: list[str] | None = None,
) -> Image.Image:
    """
    board_so_far: all community cards visible at this point in the hand
                  (accumulates across streets). Defaults to street.board.
    """
    font_sm, font_md, font_lg = _get_fonts()

    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), _hex_to_rgb(FELT_COLOR) + (255,))
    draw = ImageDraw.Draw(img)

    draw.ellipse(TABLE_BBOX, fill=(255, 255, 255, 255), outline=(220, 220, 220, 255), width=4)

    # Pot
    pot_str = f"Pot: {_fmt_pot(pot)}"
    bbox = draw.textbbox((0, 0), pot_str, font=font_lg)
    pw = bbox[2] - bbox[0]
    draw.text((TABLE_CX - pw // 2, TABLE_CY + 20), pot_str, font=font_lg, fill=POT_TEXT_COLOR)

    # Board — use accumulated cards if provided
    board = board_so_far if board_so_far is not None else street.board
    if board:
        card_gap = 8
        total_w = len(board) * CARD_W + (len(board) - 1) * card_gap
        start_x = TABLE_CX - total_w // 2 + CARD_W // 2
        for i, card_str in enumerate(board):
            rank, suit = normalise_card(card_str)
            card_img = render_card(rank, suit)
            _paste_card(img, card_img, start_x + i * (CARD_W + card_gap), BOARD_AREA_Y)

    player_map = {p.position: p for p in hand.players}
    hero_pos = next((p.position for p in hand.players if p.is_hero), None)
    active_positions = {p.position for p in hand.players}

    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    for pos, (cx, cy) in POSITION_COORDS.items():
        bx = cx - PLAYER_BOX_W // 2
        by = cy - PLAYER_BOX_H // 2
        bx2 = bx + PLAYER_BOX_W
        by2 = by + PLAYER_BOX_H

        is_hero = pos == hero_pos
        is_folded = pos in folded_positions
        player = player_map.get(pos)

        # Empty seat — always draw a dimmed placeholder so table looks full
        if player is None and pos not in active_positions:
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

    # Hero hole cards — render below the BTN box
    if hero_pos and hand.hero_cards and hero_pos in POSITION_COORDS:
        hcx, hcy = POSITION_COORDS[hero_pos]
        card_gap = 6
        total_w = len(hand.hero_cards) * CARD_W + (len(hand.hero_cards) - 1) * card_gap
        start_x = hcx - total_w // 2 + CARD_W // 2
        card_y = hcy + PLAYER_BOX_H // 2 + CARD_H // 2 + 4
        for i, cs in enumerate(hand.hero_cards):
            rank, suit = normalise_card(cs)
            card_img = render_card(rank, suit)
            _paste_card(overlay, card_img, start_x + i * (CARD_W + card_gap), card_y)

    img = Image.alpha_composite(img, overlay)

    ticker_overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    tk_draw = ImageDraw.Draw(ticker_overlay)
    tk_draw.rectangle(
        [0, CANVAS_H - TICKER_H, CANVAS_W, CANVAS_H],
        fill=TICKER_COLOR,
    )
    tbbox = tk_draw.textbbox((0, 0), action_label, font=font_md)
    tw = tbbox[2] - tbbox[0]
    th = tbbox[3] - tbbox[1]
    tx = (CANVAS_W - tw) // 2
    ty = CANVAS_H - TICKER_H + (TICKER_H - th) // 2
    tk_draw.text((tx, ty), action_label, font=font_md, fill=TICKER_TEXT_COLOR)

    img = Image.alpha_composite(img, ticker_overlay)
    return img.convert("RGB")
