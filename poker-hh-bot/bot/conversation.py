"""
In-memory session state for the PokerHandBot conversation.

State machine per user:
  IDLE           — no active hand
  ASKING_GAPS    — bot is asking gap questions one at a time
  AWAITING_CHOICE — all gaps answered; waiting for Video / Text button press
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto

from parser.schema import HandHistory


class State(Enum):
    IDLE = auto()
    ASKING_GAPS = auto()
    AWAITING_CHOICE = auto()


@dataclass
class Session:
    state: State = State.IDLE
    original_text: str = ""
    # Gaps from the most recent Claude parse: list of {"field": ..., "question": ...}
    gaps: list[dict] = field(default_factory=list)
    gap_index: int = 0
    # Accumulated (question, answer) pairs for the final re-parse
    gap_answers: list[tuple[str, str]] = field(default_factory=list)
    # Partially-parsed hand (updated after each Claude call)
    hand: HandHistory | None = None


# Keyed by Telegram user ID (int)
_sessions: dict[int, Session] = {}

# Holds the fully-resolved hand between gap completion and output button press
_completed_hands: dict[int, HandHistory] = {}


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_session(user_id: int) -> Session:
    if user_id not in _sessions:
        _sessions[user_id] = Session()
    return _sessions[user_id]


def clear_session(user_id: int) -> None:
    _sessions.pop(user_id, None)


def is_active(user_id: int) -> bool:
    s = _sessions.get(user_id)
    return s is not None and s.state != State.IDLE


def start_session(user_id: int, text: str, hand: HandHistory, gaps: list[dict]) -> Session:
    s = Session(
        state=State.ASKING_GAPS if gaps else State.AWAITING_CHOICE,
        original_text=text,
        gaps=gaps,
        gap_index=0,
        gap_answers=[],
        hand=hand,
    )
    _sessions[user_id] = s
    return s


def record_answer(user_id: int, answer: str) -> None:
    """Append the user's answer to the current gap question."""
    s = _sessions[user_id]
    current_question = s.gaps[s.gap_index]["question"]
    s.gap_answers.append((current_question, answer))
    s.gap_index += 1


def current_question(user_id: int) -> str | None:
    s = _sessions.get(user_id)
    if s and s.gap_index < len(s.gaps):
        return s.gaps[s.gap_index]["question"]
    return None


def all_gaps_answered(user_id: int) -> bool:
    s = _sessions.get(user_id)
    return s is not None and s.gap_index >= len(s.gaps)


def set_awaiting_choice(user_id: int, hand: HandHistory) -> None:
    _sessions[user_id].state = State.AWAITING_CHOICE
    _completed_hands[user_id] = hand


# ---------------------------------------------------------------------------
# Completed hand helpers
# ---------------------------------------------------------------------------

def get_completed_hand(user_id: int) -> HandHistory | None:
    return _completed_hands.get(user_id)


def clear_completed_hand(user_id: int) -> None:
    _completed_hands.pop(user_id, None)
