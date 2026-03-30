from __future__ import annotations
import os
import subprocess
import tempfile

from PIL import Image

from parser.schema import HandHistory, Street, Action
from renderer.frame_builder import build_frame, build_showdown_frame

FRAMES_PER_ACTION = 1
FPS = 24


def _action_label(action: Action) -> str:
    parts = [action.position, action.action.upper()]
    if action.amount is not None:
        val = action.amount
        parts.append(f"{int(val) if val == int(val) else val:g} BB")
    if action.is_allin:
        parts.append("ALL-IN")
    return "  ".join(parts)


def _villain_position(hand: HandHistory, folded: set[str]) -> str | None:
    """Return the position of the first non-hero, non-folded player."""
    for p in hand.players:
        if not p.is_hero and p.position not in folded:
            return p.position
    # Fallback: any non-hero (e.g. everyone folded on river)
    for p in hand.players:
        if not p.is_hero:
            return p.position
    return None


def _build_frame_sequence(hand: HandHistory) -> list[Image.Image]:
    frames: list[Image.Image] = []
    folded: set[str] = set()
    board_so_far: list[str] = []
    running_pot: float = 0

    for street in hand.streets:
        board_so_far = board_so_far + street.board
        running_pot = street.pot_start

        for action in street.actions:
            if action.action == "fold":
                folded.add(action.position)
            elif action.amount is not None:
                running_pot += action.amount

            label = _action_label(action)
            frame = build_frame(
                hand=hand,
                street=street,
                action=action,
                pot=running_pot,
                folded_positions=set(folded),
                action_label=label,
                board_so_far=board_so_far,
            )
            frames.append(frame)

    # Showdown frame — only if hand has villain cards or a result to reveal
    if hand.villain_cards or hand.result:
        villain_pos = _villain_position(hand, folded)
        frames.append(build_showdown_frame(
            hand=hand,
            board_so_far=board_so_far,
            pot=running_pot,
            folded_positions=folded,
            villain_pos=villain_pos,
        ))

    return frames


def _write_concat_file(frame_paths: list[str], concat_path: str) -> None:
    with open(concat_path, "w") as f:
        f.write("ffconcat version 1.0\n")
        for path in frame_paths:
            f.write(f"file '{path}'\n")
            f.write(f"duration {FRAMES_PER_ACTION}\n")
        if frame_paths:
            f.write(f"file '{frame_paths[-1]}'\n")


def render_video(hand: HandHistory, output_path: str | None = None) -> str:
    frames = _build_frame_sequence(hand)

    if not frames:
        raise ValueError("No frames generated — hand has no actions.")

    if len(frames) > 60:
        frames = frames[:60]

    with tempfile.TemporaryDirectory() as tmpdir:
        frame_paths: list[str] = []
        for i, img in enumerate(frames):
            png_path = os.path.join(tmpdir, f"frame_{i:04d}.png")
            img.save(png_path)
            frame_paths.append(png_path)

        concat_path = os.path.join(tmpdir, "concat.txt")
        _write_concat_file(frame_paths, concat_path)

        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_path,
            "-vf", f"fps={FPS},scale={1280}:{720}",
            "-c:v", "libx264", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            output_path,
        ]

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
        )

        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            raise RuntimeError(f"FFmpeg failed (rc={result.returncode}):\n{err}")

    return output_path
