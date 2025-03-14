
import asyncio
import logging
import os
import signal
import sys
from bot.bot import bot_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Handle termination signals
def handle_exit(signum, frame):
    logger.info("Stopping bot due to signal...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

if __name__ == "__main__":
    try:
        # Run the bot
        asyncio.run(bot_app.main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)
