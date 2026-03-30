"""
Assembles a sequence of PIL Image frames into an H.264 MP4 using FFmpeg.

Each action gets exactly 1 second of screen time (24 frames, but we use
the concat demuxer so we only write one PNG per unique frame).
"""
from __future__ import annotations
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from parser.schema import HandHistory, Street, Action
from renderer.frame_builder import build_frame

FRAMES_PER_ACTION = 1   # seconds each action is held
FPS = 24


# ---------------------------------------------------------------------------
# Action label helpers
# ---------------------------------------------------------------------------

def _action_label(action: Action) -> str:
    parts = [action.position, action.action.upper()]
    if action.amount is not None:
        parts.append(f"${action.amount:,}")
    if action.is_allin:
        parts.append("ALL-IN")
    return "  ".join(parts)


# ---------------------------------------------------------------------------
# Frame sequence builder
# ---------------------------------------------------------------------------

def _build_frame_sequence(hand: HandHistory) -> list[Image.Image]:
    """Walk every street and action, building one PIL Image per action."""
    frames: list[Image.Image] = []
    folded: set[str] = set()
    known_positions = {p.position for p in hand.players}

    for street in hand.streets:
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
                folded_positions=folded,
                action_label=label,
            )
            frames.append(frame)

    return frames


# ---------------------------------------------------------------------------
# FFmpeg assembly
# ---------------------------------------------------------------------------

def _write_concat_file(frame_paths: list[str], concat_path: str) -> None:
    """Write an ffconcat manifest with 1-second durations."""
    with open(concat_path, "w") as f:
        f.write("ffconcat version 1.0\n")
        for path in frame_paths:
            f.write(f"file '{path}'\n")
            f.write(f"duration {FRAMES_PER_ACTION}\n")
        # FFmpeg concat needs the last file listed twice (or duration on last entry
        # is sometimes dropped).  Repeat final frame with 0 duration to flush.
        if frame_paths:
            f.write(f"file '{frame_paths[-1]}'\n")


def render_video(hand: HandHistory, output_path: str | None = None) -> str:
    """
    Build the MP4 for the given hand.  Returns the path to the output file.
    Caller is responsible for deleting the file when done.
    """
    frames = _build_frame_sequence(hand)

    if not frames:
        raise ValueError("No frames generated — hand has no actions.")

    # Guard: cap at 60 seconds total
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
            # Create a temp file that persists after this function returns
            fd, output_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)

        cmd = [
            "ffmpeg",
            "-y",                           # overwrite without prompt
            "-f", "concat",
            "-safe", "0",
            "-i", concat_path,
            "-vf", f"fps={FPS},scale={1280}:{720}",
            "-c:v", "libx264",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )

        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            raise RuntimeError(f"FFmpeg failed (rc={result.returncode}):\n{err}")

    return output_path
