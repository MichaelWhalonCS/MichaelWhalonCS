import re

# ---------------------------------------------------------------------------
# Hand-history detection
# ---------------------------------------------------------------------------

_STREET_KEYWORDS = frozenset({"flop", "turn", "river", "preflop", "pre-flop"})

# Match as whole words (word boundary) so "button" doesn't trigger "btn"
_POSITION_PATTERN = re.compile(
    r"\b(btn|co|bb|sb|hj|utg\+1|utg|lj|mp|hijack|cutoff|button|blinds?)\b",
    re.IGNORECASE,
)

# Bet-sizing / action patterns
_BET_PATTERNS = [
    re.compile(r"\braises?\s+to\b", re.IGNORECASE),
    re.compile(r"\b3.?bets?\b", re.IGNORECASE),
    re.compile(r"\b4.?bets?\b", re.IGNORECASE),
    re.compile(r"\bbets?\b", re.IGNORECASE),
    re.compile(r"\bcalls?\b", re.IGNORECASE),
    re.compile(r"\bfolds?\b", re.IGNORECASE),
    re.compile(r"\bchecks?\b", re.IGNORECASE),
    re.compile(r"\bjams?\b", re.IGNORECASE),
    re.compile(r"\ball.?in\b", re.IGNORECASE),
    re.compile(r"\$\s*\d+"),
    re.compile(r"\d+\s*bb\b", re.IGNORECASE),
]


def looks_like_hand_history(text: str) -> bool:
    """
    Heuristic to decide whether a Telegram message contains a poker hand
    history rather than ordinary conversation.

    Scoring:
      street_hits   — count of distinct street keywords present
      position_hits — count of distinct poker position tokens present
      bet_hits      — count of distinct bet-sizing / action patterns matched

    Rules (any one sufficient):
      • street_hits >= 1 AND position_hits >= 1
      • street_hits >= 1 AND bet_hits >= 2
      • street_hits >= 2 AND bet_hits >= 1
      • position_hits >= 2 AND bet_hits >= 2  (e.g. no street label but clear action)
    """
    text_lower = text.lower()

    street_hits = sum(1 for kw in _STREET_KEYWORDS if kw in text_lower)
    position_hits = len(_POSITION_PATTERN.findall(text))
    bet_hits = sum(1 for pat in _BET_PATTERNS if pat.search(text))

    if street_hits >= 1 and position_hits >= 1:
        return True
    if street_hits >= 1 and bet_hits >= 2:
        return True
    if street_hits >= 2 and bet_hits >= 1:
        return True
    if position_hits >= 2 and bet_hits >= 2:
        return True

    return False


# ---------------------------------------------------------------------------
# Card normalisation helpers
# ---------------------------------------------------------------------------

_SUIT_UNICODE = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
_RANK_NORM = {str(n): str(n) for n in range(2, 10)}
_RANK_NORM.update({"t": "T", "T": "T", "j": "J", "J": "J",
                   "q": "Q", "Q": "Q", "k": "K", "K": "K",
                   "a": "A", "A": "A"})


def normalise_card(card: str) -> tuple[str, str]:
    """
    Accept cards in any common notation and return (rank, suit_symbol).
    Supports: "As", "Kh", "A♠", "K♥", "2d", "Tc" etc.
    """
    card = card.strip()
    if len(card) < 2:
        return "?", "?"

    # Unicode suit already present
    if card[-1] in "♠♥♦♣":
        rank = card[:-1].upper()
        suit = card[-1]
        return rank, suit

    # Letter suit
    rank_raw = card[:-1]
    suit_raw = card[-1].lower()
    rank = _RANK_NORM.get(rank_raw, rank_raw.upper())
    suit = _SUIT_UNICODE.get(suit_raw, "?")
    return rank, suit
