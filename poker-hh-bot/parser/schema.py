from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class VillainRead(BaseModel):
    position: str
    notes: str


class Player(BaseModel):
    position: str
    stack: Optional[float] = None   # stack in BBs at start of hand
    is_hero: bool = False
    villain_read: Optional[VillainRead] = None


class Action(BaseModel):
    position: str
    # Post-flop: "bet" = first aggression, "raise" = subsequent aggression.
    # Preflop: "raise" = open/3bet open, "3bet", "4bet", "jam".
    # Passive: "fold", "check", "call".
    action: str
    amount: Optional[float] = None
    is_allin: bool = False


class Street(BaseModel):
    name: str  # preflop / flop / turn / river
    board: list[str] = Field(default_factory=list)
    pot_start: float = 0.0
    actions: list[Action] = Field(default_factory=list)
    pot_end: float = 0.0


class HandHistory(BaseModel):
    venue: str = ""
    stakes: str = ""
    bb_size: float = 0
    is_tournament: bool = False
    effective_stack: Optional[float] = None   # smallest stack at start, in BBs
    # Tournament info (nice-to-have; None = unknown)
    players_remaining: Optional[int] = None   # players left in the field
    players_cashing: Optional[int] = None     # how many places pay out
    players: list[Player] = Field(default_factory=list)
    streets: list[Street] = Field(default_factory=list)
    hero_cards: Optional[list[str]] = None
    villain_cards: Optional[list[str]] = None
    result: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
