import json
import anthropic

from parser.schema import HandHistory
from parser.prompt import SYSTEM_PROMPT
from config import ANTHROPIC_API_KEY

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def parse_hand(
    text: str,
    gap_answers: list[tuple[str, str]] | None = None,
) -> tuple[HandHistory, list[dict]]:
    """
    Send hand history (and any accumulated gap answers) to Claude.
    Returns a (HandHistory, gaps) tuple where gaps is a list of
    {"field": ..., "question": ...} dicts.
    """
    user_message = text

    if gap_answers:
        user_message += "\n\nAdditional information provided by the player:\n"
        for question, answer in gap_answers:
            user_message += f"Q: {question}\nA: {answer}\n"

    schema_json = json.dumps(HandHistory.model_json_schema(), indent=2)
    full_system = SYSTEM_PROMPT + f"\n\nJSON Schema for HandHistory:\n{schema_json}"

    client = _get_client()
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=full_system,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    result = json.loads(raw)
    _coerce_pot_sizes(result["hand"])
    hand = HandHistory(**result["hand"])
    gaps = result.get("gaps", [])

    _normalize_bet_raise(hand)
    return hand, gaps


def _coerce_pot_sizes(hand_dict: dict) -> None:
    """Replace null pot_start/pot_end with 0.0 so Pydantic doesn't reject them."""
    for street in hand_dict.get("streets", []):
        if street.get("pot_start") is None:
            street["pot_start"] = 0.0
        if street.get("pot_end") is None:
            street["pot_end"] = 0.0


def _normalize_bet_raise(hand: HandHistory) -> None:
    """
    Enforce correct bet/raise terminology on post-flop streets:
      - First aggressive action on the street → 'bet'
      - Subsequent aggressive actions → 'raise'
    Preflop is left as-is (open=raise, 3bet, 4bet conventions).
    Mutates hand in place.
    """
    AGGRESSIVE = {"bet", "raise", "3bet", "4bet", "jam"}
    for street in hand.streets:
        if street.name == "preflop":
            continue
        aggression_count = 0
        for action in street.actions:
            if action.action in AGGRESSIVE and action.amount is not None:
                if aggression_count == 0:
                    action.action = "bet"
                else:
                    if action.action == "bet":
                        action.action = "raise"
                aggression_count += 1
