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
    hand = HandHistory(**result["hand"])
    gaps = result.get("gaps", [])

    return hand, gaps
