"""
Produces the formatted text hand history and the spoiler message.
"""
from parser.schema import HandHistory
from bot.utils import normalise_card

# Suit → display symbol (already unicode in our schema, but normalise anyway)
_SUIT_DISPLAY = {"♠": "♠", "♥": "♥", "♦": "♦", "♣": "♣",
                 "s": "♠", "h": "♥", "d": "♦", "c": "♣"}


def _fmt_card(card: str) -> str:
    rank, suit = normalise_card(card)
    return f"{rank}{suit}"


def _fmt_cards(cards: list[str] | None) -> str:
    if not cards:
        return "?"
    return " ".join(_fmt_card(c) for c in cards)


def _fmt_action(action) -> str:
    parts = [action.position, action.action]
    if action.amount is not None:
        parts.append(f"${action.amount:,}")
    if action.is_allin:
        parts.append("(all-in)")
    return " ".join(parts)


def build_text_history(hand: HandHistory) -> str:
    lines: list[str] = []

    # Header line
    header = hand.stakes
    if hand.venue:
        header += f" — {hand.venue}"
    lines.append(header)

    # Effective stack
    if hand.effective_stack is not None:
        lines.append(f"Eff. stack: ${hand.effective_stack:,}")

    lines.append("")

    # Villain reads
    for player in hand.players:
        if player.villain_read:
            lines.append(f"📖 {player.position}: {player.villain_read.notes}")

    # Hero cards
    hero_card_str = _fmt_cards(hand.hero_cards)
    hero_pos = next((p.position for p in hand.players if p.is_hero), "Hero")
    lines.append(f"\nHero ({hero_pos}): {hero_card_str}")
    lines.append("")

    # Streets
    for street in hand.streets:
        board_str = ""
        if street.board:
            board_str = f" ({' '.join(_fmt_card(c) for c in street.board)})"
        street_header = f"{street.name.capitalize()}{board_str} (${street.pot_start:,})"
        lines.append(street_header)

        for action in street.actions:
            lines.append(f"  {_fmt_action(action)}")

        lines.append("")

    # Result
    if hand.result:
        lines.append(f"Result: {hand.result}")

    return "\n".join(lines).strip()


def build_spoiler_message(hand: HandHistory) -> str:
    """Returns the HTML spoiler block."""
    villain_line = ""
    if hand.villain_cards:
        villain_line = f"Villain: {_fmt_cards(hand.villain_cards)}"
    else:
        villain_line = "Villain: (mucked)"

    result_line = hand.result or ""

    inner = villain_line
    if result_line:
        inner += f"\n{result_line}"

    return f"🃏 Reveal\n\n<tg-spoiler>{inner}</tg-spoiler>"
