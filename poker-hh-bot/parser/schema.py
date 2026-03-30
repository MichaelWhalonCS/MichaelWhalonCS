from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class VillainRead(BaseModel):
    position: str
    notes: str


class Player(BaseModel):
    position: str
    stack: Optional[int] = None
    is_hero: bool = False
    villain_read: Optional[VillainRead] = None


class Action(BaseModel):
    position: str
    action: str  # fold / check / call / bet / raise / 3bet / 4bet / jam
    amount: Optional[int] = None
    is_allin: bool = False


class Street(BaseModel):
    name: str  # preflop / flop / turn / river
    board: list[str] = Field(default_factory=list)
    pot_start: int
    actions: list[Action] = Field(default_factory=list)
    pot_end: int


class HandHistory(BaseModel):
    venue: str = ""
    stakes: str = ""
    bb_size: int = 0
    effective_stack: Optional[int] = None
    players: list[Player] = Field(default_factory=list)
    streets: list[Street] = Field(default_factory=list)
    hero_cards: Optional[list[str]] = None
    villain_cards: Optional[list[str]] = None
    result: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
