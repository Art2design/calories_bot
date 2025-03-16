import os
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import register_handlers

class BotApp:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Get bot token from environment variables
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            self.logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

        # Initialize bot and dispatcher
        self.bot = Bot(token=self.bot_token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        # Register handlers
        register_handlers(self.dp)

    async def main(self):
        """Main function to start the bot"""
        try:
            self.logger.info("Starting bot in polling mode...")
            await self.dp.start_polling(self.bot)
        finally:
            if hasattr(self.bot, 'session'):
                await self.bot.session.close()

bot_app = BotApp()

if __name__ == "__main__":
    asyncio.run(bot_app.main())