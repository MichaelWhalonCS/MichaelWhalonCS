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


def _fmt_amount(amount: float) -> str:
    if amount == int(amount):
        return f"{int(amount):,}"
    return f"{amount:g}"


def _fmt_action(action) -> str:
    parts = [action.position, action.action]
    if action.amount is not None:
        parts.append(_fmt_amount(action.amount))
    if action.is_allin:
        parts.append("(all-in)")
    return " ".join(parts)


def _fmt_optional_int(val: int | None) -> str:
    return str(val) if val is not None else "unknown"


def build_text_history(hand: HandHistory) -> str:
    lines: list[str] = []

    # Header line
    header = hand.stakes
    if hand.venue:
        header += f" — {hand.venue}"
    lines.append(header)

    # Effective stack
    if hand.effective_stack is not None:
        lines.append(f"Eff. stack: {_fmt_amount(hand.effective_stack)} BB")

    # Tournament info
    if hand.is_tournament:
        remaining = _fmt_optional_int(hand.players_remaining)
        cashing = _fmt_optional_int(hand.players_cashing)
        lines.append(f"Players remaining: {remaining}  |  Cashing: {cashing}")

    lines.append("")

    # Per-player stacks
    if any(p.stack is not None for p in hand.players):
        for player in hand.players:
            stack_str = f"{_fmt_amount(player.stack)} BB" if player.stack is not None else "unknown"
            hero_tag = " (Hero)" if player.is_hero else ""
            lines.append(f"  {player.position}{hero_tag}: {stack_str}")
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
    seen_board: list[str] = []
    for street in hand.streets:
        new_cards = [c for c in street.board if c not in seen_board]
        seen_board.extend(new_cards)
        board_str = ""
        if new_cards:
            board_str = f" ({' '.join(_fmt_card(c) for c in new_cards)})"
        street_header = f"{street.name.capitalize()}{board_str} ({_fmt_amount(street.pot_start)} BB)"
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
