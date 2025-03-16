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
        try:
            self.logger.info("Starting bot with webhook...")
            
            await self.bot.delete_my_commands()
            
            webhook_url = os.environ.get("WEBHOOK_URL")
            if not webhook_url:
                self.logger.error("WEBHOOK_URL not found in environment")
                return
                
            await self.bot.set_webhook(webhook_url)
            return self.dp
        except Exception as e:
            self.logger.error(f"Error in main: {e}")
            raise
        finally:
            # Ensure bot session is closed
            if hasattr(self.bot, 'session') and not self.bot.session.closed:
                await self.bot.session.close()

bot_app = BotApp()

if __name__ == "__main__":
    # Run bot if script is executed directly
    asyncio.run(bot_app.main())
