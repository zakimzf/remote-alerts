import logging
import os
import re
import subprocess
import time
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

# Files to store process ID and sleep status
PID_FILE = "bot.pid"
SLEEP_FILE = "sleep.lock"


def parse_duration(duration_str):
    """Parses a duration string like '1h30m' into seconds."""
    parts = re.match(r"((?P<hours>\d+)h)?((?P<minutes>\d+)m)?", duration_str)
    if not parts:
        return 0
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return time_params.get("hours", 0) * 3600 + time_params.get("minutes", 0) * 60

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


async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Puts the bot to sleep for a specified duration."""
    if not context.args:
        await update.message.reply_text("Please provide a duration (e.g., /sleep 1h30m).")
        return

    duration_str = context.args[0]
    duration_seconds = parse_duration(duration_str)

    if duration_seconds == 0:
        await update.message.reply_text(
            "Invalid duration format. Use 'h' for hours and 'm' for minutes (e.g., 1h30m)."
        )
        return

    wakeup_time = time.time() + duration_seconds
    with open(SLEEP_FILE, "w") as f:
        f.write(str(wakeup_time))

    await update.message.reply_text(f"Bot is now sleeping for {duration_str}.")
    logger.info(f"Bot sleeping until {time.ctime(wakeup_time)}")


async def wakeup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Wakes up the bot immediately."""
    if os.path.exists(SLEEP_FILE):
        os.remove(SLEEP_FILE)
        await update.message.reply_text("Bot has been woken up.")
        logger.info("Bot woken up by command.")
    else:
        await update.message.reply_text("Bot is not sleeping.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks the status of the bot."""
    if os.path.exists(PID_FILE):
        if os.path.exists(SLEEP_FILE):
            with open(SLEEP_FILE, "r") as f:
                wakeup_time = float(f.read())
            remaining_time = wakeup_time - time.time()
            if remaining_time > 0:
                await update.message.reply_text(
                    f"Bot is sleeping for another {remaining_time / 60:.0f} minutes."
                )
                return
        await update.message.reply_text("Bot is running.")
    else:
        await update.message.reply_text("Bot is stopped.")


def main() -> None:
    """Run the bot management."""
    application = Application.builder().token(config["telegramToken"]).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("sleep", sleep))
    application.add_handler(CommandHandler("wakeup", wakeup))
    application.add_handler(CommandHandler("status", status))

    application.run_polling()

if __name__ == "__main__":
    main()