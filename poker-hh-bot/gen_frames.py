"""
Generate test_results frames without needing the Claude API.
Run from poker-hh-bot/:  python gen_frames.py
"""
import os, sys
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")

from pathlib import Path
from parser.schema import HandHistory, Player, Street, Action
from renderer.frame_builder import build_frame, build_showdown_frame, build_question_frame

OUT = Path("test_results")
OUT.mkdir(exist_ok=True)

# ── Hand: $2/$5 NLHE 6-handed, Hero BTN, AhKd ────────────────────────────────
hand = HandHistory(
    venue="Bellagio",
    stakes="$2/$5 NL",
    bb_size=5,
    game_type="nlhe",
    effective_stack=160,   # $800 / $5
    players=[
        Player(position="UTG",   stack=160),
        Player(position="UTG+1", stack=145),
        Player(position="MP",    stack=175),
        Player(position="CO",    stack=160),
        Player(position="BTN",   stack=160, is_hero=True),
        Player(position="SB",    stack=130),
        Player(position="BB",    stack=155),
    ],
    hero_cards=["Ah", "Kd"],
    villain_cards=["Qs", "Jh"],
)

preflop = Street(
    name="preflop",
    board=[],
    pot_start=7,   # SB+BB
    actions=[
        Action(position="UTG",   action="fold"),
        Action(position="UTG+1", action="fold"),
        Action(position="MP",    action="fold"),
        Action(position="CO",    action="raise", amount=15),
        Action(position="BTN",   action="raise", amount=50),
        Action(position="SB",    action="fold"),
        Action(position="BB",    action="fold"),
        Action(position="CO",    action="call"),
    ],
    pot_end=103,
)

flop = Street(
    name="flop",
    board=["As", "Kh", "3c"],
    pot_start=103,
    actions=[
        Action(position="CO",  action="check"),
        Action(position="BTN", action="bet",  amount=60),
        Action(position="CO",  action="call"),
    ],
    pot_end=223,
)

turn = Street(
    name="turn",
    board=["As", "Kh", "3c", "7d"],
    pot_start=223,
    actions=[
        Action(position="CO",  action="check"),
        Action(position="BTN", action="bet",   amount=130),
        Action(position="CO",  action="raise", amount=320),
        Action(position="BTN", action="call"),
    ],
    pot_end=863,
)

river = Street(
    name="river",
    board=["As", "Kh", "3c", "7d", "2s"],
    pot_start=863,
    actions=[
        Action(position="CO",  action="jam",  amount=450, is_allin=True),
        Action(position="BTN", action="call"),
    ],
    pot_end=1763,
)

hand.streets = [preflop, flop, turn, river]

# ── Replay helper ──────────────────────────────────────────────────────────────

def action_label(a: Action) -> str:
    base = f"{a.position}  {a.action.upper()}"
    if a.amount:
        base += f"  {int(a.amount) if a.amount == int(a.amount) else a.amount} BB"
    if a.is_allin:
        base += "  (all-in)"
    return base


def run():
    folded: set[str] = set()
    history: list[str] = []
    frame_n = 1
    board_so_far: list[str] = []

    for street in hand.streets:
        history.append(f"▸ {street.name.upper()}  (pot {int(street.pot_start)} BB)")
        pot = street.pot_start
        board_so_far = list(street.board)

        for a in street.actions:
            lbl = action_label(a)
            history.append(f"  {a.position}: {a.action}" +
                           (f" {int(a.amount) if a.amount == int(a.amount) else a.amount}" if a.amount else ""))

            frame = build_frame(
                hand=hand,
                street=street,
                action=a,
                pot=pot,
                folded_positions=set(folded),
                action_label=lbl,
                board_so_far=board_so_far,
                action_history=list(history),
            )
            name = f"{frame_n:02d}_{street.name}_{a.position}_{a.action}.png"
            frame.save(OUT / name)
            print(f"  saved {name}")
            frame_n += 1

            if a.action == "fold":
                folded.add(a.position)
            if a.amount:
                pot += a.amount

    # Showdown
    history.append("▸ SHOWDOWN")
    frame = build_showdown_frame(
        hand=hand,
        board_so_far=board_so_far,
        pot=river.pot_end,
        folded_positions=folded,
        villain_pos="CO",
        action_history=history,
    )
    frame.save(OUT / f"{frame_n:02d}_showdown.png")
    print(f"  saved {frame_n:02d}_showdown.png")
    frame_n += 1

    # Question frame (demo — pretend villain mucks)
    hand2 = hand.model_copy(update={"villain_cards": None})
    frame = build_question_frame(
        hand=hand2,
        board_so_far=board_so_far,
        pot=river.pot_end,
        folded_positions=folded,
        action_history=history[:-1],
    )
    frame.save(OUT / f"{frame_n:02d}_question.png")
    print(f"  saved {frame_n:02d}_question.png")

    print(f"\nDone — {frame_n} frames in {OUT}/")


if __name__ == "__main__":
    run()
