from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont

CARD_W = 70
CARD_H = 100
CORNER_RADIUS = 8

SUIT_COLORS = {
    "♠": "#1a1a1a", "♥": "#CC0000", "♦": "#0066CC", "♣": "#2E7D32",
    "s": "#1a1a1a", "h": "#CC0000", "d": "#0066CC", "c": "#2E7D32",
    "?": "#888888",   # unknown suit → grey
}

SUIT_SYMBOLS = {
    "♠": "♠", "♥": "♥", "♦": "♦", "♣": "♣",
    "s": "♠", "h": "♥", "d": "♦", "c": "♣",
    "?": "?",          # unknown suit → question mark
}


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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


def render_card(rank: str, suit: str) -> Image.Image:
    color_hex = SUIT_COLORS.get(suit, "#1a1a1a")
    suit_sym = SUIT_SYMBOLS.get(suit, suit)
    color_rgb = tuple(int(color_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [0, 0, CARD_W - 1, CARD_H - 1],
        radius=CORNER_RADIUS,
        fill=(255, 255, 255, 255),
        outline=color_rgb + (255,),
        width=2,
    )

    small_font = _get_font(13)
    big_font = _get_font(34)

    label = f"{rank}{suit_sym}"
    draw.text((4, 2), label, font=small_font, fill=color_rgb + (255,))

    bbox = draw.textbbox((0, 0), suit_sym, font=big_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (CARD_W - text_w) // 2 - bbox[0]
    y = (CARD_H - text_h) // 2 - bbox[1]
    draw.text((x, y), suit_sym, font=big_font, fill=color_rgb + (255,))

    return img


def render_card_back() -> Image.Image:
    back_color = (26, 42, 108)
    line_color = (60, 80, 160)
    border_color = (200, 200, 220)

    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [0, 0, CARD_W - 1, CARD_H - 1],
        radius=CORNER_RADIUS,
        fill=back_color + (255,),
        outline=border_color + (255,),
        width=2,
    )

    spacing = 8
    for i in range(-CARD_H, CARD_W + CARD_H, spacing):
        draw.line([(i, 0), (i + CARD_H, CARD_H)], fill=line_color + (180,), width=1)
        draw.line([(i, CARD_H), (i + CARD_H, 0)], fill=line_color + (180,), width=1)

    return img


def render_cards(card_strings: list[str], face_down: bool = False) -> list[Image.Image]:
    from bot.utils import normalise_card

    images = []
    for cs in card_strings:
        if face_down:
            images.append(render_card_back())
        else:
            rank, suit = normalise_card(cs)
            images.append(render_card(rank, suit))
    return images
