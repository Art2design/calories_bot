
import asyncio
import logging
import os
import signal
import sys
from bot.bot import bot_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log environment check
logger.info("Starting Telegram bot...")
logger.info("Environment variables check:")
required_vars = [
    "TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "DATABASE_URL",
    "PGDATABASE", "PGHOST", "PGPORT", "PGUSER", "PGPASSWORD"
]
for var in required_vars:
    logger.info(f"{var} present: {bool(os.environ.get(var))}")

# Handle termination signals
def handle_exit(signum, frame):
    logger.info("Stopping bot due to signal...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

if __name__ == "__main__":
    try:
        asyncio.run(bot_app.main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)
