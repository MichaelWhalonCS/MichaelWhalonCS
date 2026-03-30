"""
End-to-end test — no Telegram needed.
Run from the poker-hh-bot/ directory:
    python test_local.py
"""
import os, sys, tempfile

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))

SAMPLE_HAND = """
$2/$5 NL at Bellagio. 6-handed.
Villain in CO is a loose aggressive reg, 3-bets light, loves to barrel.
Effective stacks $800.

Preflop: Hero is BTN with Ah Kd.
CO raises to $15. Hero 3-bets to $50. CO calls.

Flop: As Kh 3c (pot $103)
CO checks. Hero bets $60. CO calls.

Turn: 7d (pot $223)
CO checks. Hero bets $130. CO raises to $320. Hero calls.

River: 2s (pot $863)
CO jams $450. Hero calls.

CO shows Qs Jh (missed gutshot). Hero wins $1763.
"""

# ── 1. Parser ──────────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1: Parsing hand via Claude API")
print("=" * 60)

from parser.claude_parser import parse_hand
hand, gaps = parse_hand(SAMPLE_HAND)

print(f"  Venue:           {hand.venue}")
print(f"  Stakes:          {hand.stakes}")
print(f"  Eff. stack:      {hand.effective_stack}")
print(f"  Hero cards:      {hand.hero_cards}")
print(f"  Villain cards:   {hand.villain_cards}")
print(f"  Streets:         {[s.name for s in hand.streets]}")
print(f"  Gaps returned:   {gaps}")
print()

# ── 2. Formatter ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 2: Formatted text output")
print("=" * 60)

from bot.formatter import build_text_history, build_spoiler_message
text_out = build_text_history(hand)
spoiler   = build_spoiler_message(hand)
print(text_out)
print()
print(spoiler)
print()

# ── 3. Renderer — single frame ────────────────────────────────────────────
print("=" * 60)
print("STEP 3: Rendering a single frame (Pillow only)")
print("=" * 60)

if hand.streets:
    street = hand.streets[0]
    action = street.actions[0] if street.actions else None
    if action:
        from renderer.frame_builder import build_frame
        frame = build_frame(
            hand=hand,
            street=street,
            action=action,
            pot=street.pot_start,
            folded_positions=set(),
            action_label=f"{action.position}  {action.action.upper()}",
        )
        fd, png_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        frame.save(png_path)
        print(f"  Frame saved to: {png_path}  ({frame.size[0]}×{frame.size[1]})")
    else:
        print("  (no actions on first street, skipping frame)")
else:
    print("  (no streets parsed, skipping frame)")
print()

# ── 4. Full video (requires ffmpeg) ───────────────────────────────────────
print("=" * 60)
print("STEP 4: Full video render (requires ffmpeg)")
print("=" * 60)

import shutil
if not shutil.which("ffmpeg"):
    print("  ffmpeg not found — skipping video render.")
    print("  Install with:  apt-get install ffmpeg  (or brew install ffmpeg)")
else:
    from renderer.video import render_video
    mp4_path = render_video(hand)
    size_kb = os.path.getsize(mp4_path) // 1024
    print(f"  Video saved to: {mp4_path}  ({size_kb} KB)")

print()
print("All tests passed ✓")
