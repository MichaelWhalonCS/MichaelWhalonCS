"""
Telegram update handlers for PokerHandBot.

Flow
----
1. Any message → looks_like_hand_history() check.
2. Yes → Claude parses it → gaps queued.
3. If gaps exist, ask them one at a time.
4. When done → re-parse with all answers → show Video / Text inline keyboard.
5. Callback: generate output, send, clear session.
"""
from __future__ import annotations
import asyncio
import logging
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import conversation as conv
from bot.conversation import State
from bot.formatter import build_text_history, build_spoiler_message
from bot.utils import looks_like_hand_history
from parser.claude_parser import parse_hand, parse_hand_from_image
from parser.schema import HandHistory

log = logging.getLogger(__name__)

# Callback data constants
CB_VIDEO = "output_video"
CB_TEXT = "output_text"

_OUTPUT_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🎬 Video", callback_data=CB_VIDEO),
            InlineKeyboardButton("📝 Formatted Text", callback_data=CB_TEXT),
        ]
    ]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_id(update: Update) -> int:
    return update.effective_user.id  # type: ignore[union-attr]


async def _reply(update: Update, text: str, **kwargs) -> None:
    await update.effective_message.reply_text(text, **kwargs)  # type: ignore[union-attr]


async def _ask_next_gap(update: Update, user_id: int) -> None:
    question = conv.current_question(user_id)
    if question:
        await _reply(update, f"❓ {question}")


async def _transition_to_choice(update: Update, user_id: int) -> None:
    """
    All gaps answered.  Do a final re-parse incorporating all answers,
    store the completed hand, and show the output keyboard.
    """
    session = conv.get_session(user_id)
    image_bytes = getattr(session, "image_bytes", None)
    try:
        if image_bytes is not None:
            hand, _ = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: parse_hand_from_image(
                    bytes(image_bytes),
                    media_type="image/jpeg",
                    gap_answers=session.gap_answers,
                ),
            )
        else:
            hand, _ = await asyncio.get_event_loop().run_in_executor(
                None,
                parse_hand,
                session.original_text,
                session.gap_answers,
            )
    except Exception as exc:
        log.exception("Re-parse failed for user %s", user_id)
        await _reply(update, f"⚠️ Couldn't re-parse the hand: {exc}\nPlease try again.")
        conv.clear_session(user_id)
        return

    conv.set_awaiting_choice(user_id, hand)
    await _reply(
        update,
        "Got it! How would you like to see this hand?",
        reply_markup=_OUTPUT_KEYBOARD,
    )


# ---------------------------------------------------------------------------
# Message handler (text messages)
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_id = _user_id(update)
    text = update.message.text.strip()

    # --- User is answering a gap question -----------------------------------
    if conv.is_active(user_id):
        session = conv.get_session(user_id)
        if session.state == State.ASKING_GAPS:
            conv.record_answer(user_id, text)

            if conv.all_gaps_answered(user_id):
                await _transition_to_choice(update, user_id)
            else:
                await _ask_next_gap(update, user_id)
            return

        if session.state == State.AWAITING_CHOICE:
            # Ignore stray text while waiting for a button press
            return

    # --- Detect new hand history --------------------------------------------
    if not looks_like_hand_history(text):
        return  # ignore unrelated chat

    await _reply(update, "🃏 Parsing your hand history…")

    try:
        hand, gaps = await asyncio.get_event_loop().run_in_executor(
            None, parse_hand, text, None
        )
    except Exception as exc:
        log.exception("Initial parse failed for user %s", user_id)
        await _reply(update, f"⚠️ Couldn't parse the hand: {exc}\nPlease try again.")
        return

    session = conv.start_session(user_id, text, hand, gaps)

    if gaps:
        await _ask_next_gap(update, user_id)
    else:
        await _transition_to_choice(update, user_id)


# ---------------------------------------------------------------------------
# Callback query handler (inline button presses)
# ---------------------------------------------------------------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    user_id = _user_id(update)
    data = query.data

    hand = conv.get_completed_hand(user_id)
    if hand is None:
        await query.edit_message_text("⚠️ Session expired. Please paste the hand again.")
        return

    # Clean up immediately so the user can paste a new hand straight away
    conv.clear_session(user_id)
    conv.clear_completed_hand(user_id)

    if data == CB_TEXT:
        await _send_text_output(update, hand)
    elif data == CB_VIDEO:
        await _send_video_output(update, hand)


async def _send_text_output(update: Update, hand: HandHistory) -> None:
    formatted = build_text_history(hand)
    spoiler = build_spoiler_message(hand)

    await update.effective_message.reply_text(  # type: ignore[union-attr]
        f"```\n{formatted}\n```",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    await update.effective_message.reply_text(  # type: ignore[union-attr]
        spoiler,
        parse_mode=ParseMode.HTML,
    )


async def _send_video_output(update: Update, hand: HandHistory) -> None:
    msg = update.effective_message
    assert msg is not None

    status = await msg.reply_text("🎬 Rendering video…")

    mp4_path: str | None = None
    try:
        mp4_path = await asyncio.get_event_loop().run_in_executor(
            None, _render_video_sync, hand
        )
        with open(mp4_path, "rb") as f:
            await msg.reply_video(video=f, supports_streaming=True)

        spoiler = build_spoiler_message(hand)
        await msg.reply_text(spoiler, parse_mode=ParseMode.HTML)

    except Exception as exc:
        log.exception("Video render failed for hand")
        await msg.reply_text(f"⚠️ Video rendering failed: {exc}\nSending text instead.")
        await _send_text_output(update, hand)
    finally:
        if mp4_path and os.path.exists(mp4_path):
            os.unlink(mp4_path)
        await status.delete()


def _render_video_sync(hand: HandHistory) -> str:
    """Blocking call to the video renderer (runs in executor thread)."""
    from renderer.video import render_video
    return render_video(hand)


# ---------------------------------------------------------------------------
# Photo handler (image → parse via Claude vision)
# ---------------------------------------------------------------------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle an image message: download the photo, send to Claude vision."""
    if not update.message or not update.message.photo:
        return

    user_id = _user_id(update)

    # If user is answering a gap question with an image, ignore (text only)
    if conv.is_active(user_id):
        return

    await _reply(update, "🃏 Reading hand history from image…")

    # Get highest-resolution photo
    photo = update.message.photo[-1]
    tg_file = await photo.get_file()
    image_bytes = await tg_file.download_as_bytearray()

    try:
        hand, gaps = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: parse_hand_from_image(bytes(image_bytes), media_type="image/jpeg"),
        )
    except Exception as exc:
        log.exception("Image parse failed for user %s", user_id)
        await _reply(update, f"⚠️ Couldn't parse the hand from image: {exc}\nPlease try again.")
        return

    # Use a placeholder text so gap re-parse can work (image not re-sent)
    placeholder = "[image]"
    session = conv.start_session(user_id, placeholder, hand, gaps)
    # Store the image bytes so we can re-parse with them if gaps exist
    session.image_bytes = image_bytes  # type: ignore[attr-defined]

    if gaps:
        await _ask_next_gap(update, user_id)
    else:
        await _transition_to_choice(update, user_id)
