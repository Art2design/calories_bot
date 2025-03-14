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
        # In aiogram 3.x, Dispatcher doesn't take bot as a parameter
        self.dp = Dispatcher(storage=self.storage)
        
        # Register handlers
        register_handlers(self.dp)
    
    async def main(self):
        """Main function to start the bot"""
        self.logger.info("Starting bot...")
        
        # Start polling (aiogram 3.x way)
        try:
            # In aiogram 3.x, polling is started differently
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
        finally:
            # In aiogram 3.x, session closing is handled automatically
            self.logger.info("Bot stopped")

bot_app = BotApp()

if __name__ == "__main__":
    # Run bot if script is executed directly
    asyncio.run(bot_app.main())
