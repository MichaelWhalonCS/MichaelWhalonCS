"""
Entry point: python -m bot.main
"""
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from bot.handlers import handle_callback, handle_message

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def main() -> None:
    log.info("Starting PokerHandBot…")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handle all text messages (groups + DMs, no admin rights required)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Handle inline button presses
    app.add_handler(CallbackQueryHandler(handle_callback))

    log.info("Bot is running. Press Ctrl-C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
