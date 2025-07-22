import logging
import os
import subprocess
import yaml
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read config
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
config_file = "config.yml"
if os.path.isfile("config.dev.yml"):
    config_file = "config.dev.yml"

with open(os.path.join(__location__, config_file), "r", encoding="utf-8") as yaml_file:
    config = yaml.load(yaml_file, Loader=yaml.FullLoader)

# File to store the process ID
PID_FILE = "bot.pid"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the pump alert bot."""
    if os.path.exists(PID_FILE):
        await update.message.reply_text("Bot is already running.")
        return

    # Start the bot as a new process
    process = subprocess.Popen(["python", "pumpAlerts.py"])
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    await update.message.reply_text("Bot started successfully.")
    logger.info(f"Bot started with PID: {process.pid}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops the pump alert bot."""
    if not os.path.exists(PID_FILE):
        await update.message.reply_text("Bot is not running.")
        return

    with open(PID_FILE, "r") as f:
        pid = int(f.read())

    try:
        # Terminate the process
        p = subprocess.Popen(["kill", str(pid)])
        p.wait()
        os.remove(PID_FILE)
        await update.message.reply_text("Bot stopped successfully.")
        logger.info(f"Bot with PID: {pid} stopped.")
    except Exception as e:
        await update.message.reply_text(f"Error stopping bot: {e}")
        logger.error(f"Error stopping bot with PID {pid}: {e}")

def main() -> None:
    """Run the bot management."""
    application = Application.builder().token(config["telegramToken"]).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    application.run_polling()

if __name__ == "__main__":
    main()