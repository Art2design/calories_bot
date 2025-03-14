
import asyncio
import logging
from bot.bot import bot_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Run the bot
    asyncio.run(bot_app.main())
