import os
import logging
from flask import Flask, render_template
import sys
#import subprocess
#import signal
#import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

#@app.route(f"/webhook/{os.environ.get('TELEGRAM_BOT_TOKEN')}", methods=['POST'])
#def webhook():
#    """Handle incoming webhook updates"""
#    update = request.get_json()
#    # Use asyncio to handle async bot operations
#    import asyncio
#    loop = asyncio.new_event_loop()
#    asyncio.set_event_loop(loop)
#    dispatcher = loop.run_until_complete(telegram_bot.main())
#    loop.run_until_complete(dispatcher.feed_webhook_update(update))
#    loop.close()
#    return '', 200

#def kill_bot_process():
#    """Kill bot process on exit"""
#    global bot_process
#    if bot_process is not None:
#        logger.info("Stopping Telegram bot...")
#        try:
#            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
#            logger.info("Telegram bot stopped")
#        except Exception as e:
#            logger.error(f"Error stopping bot: {e}")

#def start_bot_process():
#    """Start the bot in a separate process"""
#    global bot_process
    
#    # Убиваем существующие процессы бота перед запуском нового и обрабатываем зомби-процессы
#    try:
#        # Используем SIGKILL для гарантированного завершения процессов
#        subprocess.run("pkill -9 -f 'python run_bot.py'", shell=True)
#        # Пытаемся убить зомби-процессы run_bot.py
#        subprocess.run("ps aux | grep 'defunct' | grep 'python' | awk '{print $2}' | xargs -r kill -9", shell=True)
#        # Ждем немного, чтобы процессы завершились
#        import time
#        time.sleep(2)
#    except Exception as e:
#        logger.error(f"Error while killing bot processes: {e}")
#        pass
    
#    if bot_process is None or bot_process.poll() is not None:
#        # Запускаем отдельный скрипт для бота в отдельном процессе
#        logger.info("Starting the Telegram bot...")
        
#        # Создаем отдельный скрипт для запуска бота
#        with open('run_bot.py', 'w') as f:
#            f.write("""
#import asyncio
#import logging
#import os
#import signal
#import sys
#from bot.bot import bot_app
#
## Configure logging
#logging.basicConfig(level=logging.INFO)
#logger = logging.getLogger(__name__)
#
## Handle termination signals
#def handle_exit(signum, frame):
#    logger.info("Stopping bot due to signal...")
#    sys.exit(0)
#
#signal.signal(signal.SIGTERM, handle_exit)
#signal.signal(signal.SIGINT, handle_exit)
#
#if __name__ == "__main__":
#    try:
#        # Run the bot
#        asyncio.run(bot_app.main())
#    except KeyboardInterrupt:
#        logger.info("Bot stopped by keyboard interrupt")
#    except Exception as e:
#        logger.error(f"Bot error: {e}")
#        sys.exit(1)
#""")
        
#        # Запускаем скрипт в отдельном процессе с созданием новой группы процессов
#        bot_process = subprocess.Popen([sys.executable, 'run_bot.py'], 
#                                       preexec_fn=os.setsid)
#        logger.info("Telegram bot started in background (PID: %s)", bot_process.pid)
        
#        # Регистрируем функцию для очистки при выходе
#        atexit.register(kill_bot_process)

# Запускаем бота при старте приложения
#with app.app_context():
#    start_bot_process()

@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)