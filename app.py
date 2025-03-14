import os
import logging
from flask import Flask, render_template
import asyncio
from threading import Thread

from bot.bot import bot_app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Bot running flag
bot_started = False

def run_bot():
    """Run the bot in a separate thread"""
    asyncio.run(bot_app.main())

# В современных версиях Flask вместо before_first_request 
# используется app.app_context и вызов функции после определения приложения
def start_bot():
    """Start the bot"""
    global bot_started
    if not bot_started:
        logger.info("Starting the Telegram bot...")
        Thread(target=run_bot, daemon=True).start()
        bot_started = True
        logger.info("Telegram bot started in background")

# Запускаем бота при старте приложения
with app.app_context():
    start_bot()

@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
