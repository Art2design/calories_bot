import os
import logging
from flask import Flask, render_template
import multiprocessing
import sys
import subprocess

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Bot process
bot_process = None

def start_bot_process():
    """Start the bot in a separate process"""
    global bot_process
    if bot_process is None or bot_process.poll() is not None:
        # Запускаем отдельный скрипт для бота в отдельном процессе
        logger.info("Starting the Telegram bot...")
        
        # Создаем отдельный скрипт для запуска бота
        with open('run_bot.py', 'w') as f:
            f.write("""
import asyncio
import logging
from bot.bot import bot_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Run the bot
    asyncio.run(bot_app.main())
""")
        
        # Запускаем скрипт в отдельном процессе
        bot_process = subprocess.Popen([sys.executable, 'run_bot.py'])
        logger.info("Telegram bot started in background")

# Запускаем бота при старте приложения
with app.app_context():
    start_bot_process()

@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
