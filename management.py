import logging
import os
import re
import subprocess
import time
import yaml
import telebot

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

bot = telebot.TeleBot(config["telegramToken"])


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


@bot.message_handler(commands=["start"])
def start(message):
    """Starts the pump alert bot."""
    if os.path.exists(PID_FILE):
        bot.reply_to(message, "Bot is already running.")
        return

    # Start the bot as a new process
    process = subprocess.Popen(["python", "pumpAlerts.py"])
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    bot.reply_to(message, "Bot started successfully.")
    logger.info(f"Bot started with PID: {process.pid}")


@bot.message_handler(commands=["stop"])
def stop(message):
    """Stops the pump alert bot."""
    if not os.path.exists(PID_FILE):
        bot.reply_to(message, "Bot is not running.")
        return

    with open(PID_FILE, "r") as f:
        pid = int(f.read())

    try:
        # Terminate the process
        if os.name == "nt":
            subprocess.Popen(["taskkill", "/F", "/T", "/PID", str(pid)])
        else:
            subprocess.Popen(["kill", str(pid)])
        os.remove(PID_FILE)
        bot.reply_to(message, "Bot stopped successfully.")
        logger.info(f"Bot with PID: {pid} stopped.")
    except Exception as e:
        bot.reply_to(message, f"Error stopping bot: {e}")
        logger.error(f"Error stopping bot with PID {pid}: {e}")


@bot.message_handler(commands=["sleep"])
def sleep(message):
    """Puts the bot to sleep for a specified duration."""
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Please provide a duration (e.g., /sleep 1h30m).")
        return

    duration_str = args[1]
    duration_seconds = parse_duration(duration_str)

    if duration_seconds == 0:
        bot.reply_to(
            message,
            "Invalid duration format. Use 'h' for hours and 'm' for minutes (e.g., 1h30m).",
        )
        return

    wakeup_time = time.time() + duration_seconds
    with open(SLEEP_FILE, "w") as f:
        f.write(str(wakeup_time))

    bot.reply_to(message, f"Bot is now sleeping for {duration_str}.")
    logger.info(f"Bot sleeping until {time.ctime(wakeup_time)}")


@bot.message_handler(commands=["wakeup"])
def wakeup(message):
    """Wakes up the bot immediately."""
    if os.path.exists(SLEEP_FILE):
        os.remove(SLEEP_FILE)
        bot.reply_to(message, "Bot has been woken up.")
        logger.info("Bot woken up by command.")
    else:
        bot.reply_to(message, "Bot is not sleeping.")


@bot.message_handler(commands=["status"])
def status(message):
    """Checks the status of the bot."""
    if os.path.exists(PID_FILE):
        if os.path.exists(SLEEP_FILE):
            with open(SLEEP_FILE, "r") as f:
                wakeup_time = float(f.read())
            remaining_time = wakeup_time - time.time()
            if remaining_time > 0:
                bot.reply_to(
                    message,
                    f"Bot is sleeping for another {remaining_time / 60:.0f} minutes.",
                )
                return
        bot.reply_to(message, "Bot is running.")
    else:
        bot.reply_to(message, "Bot is stopped.")


if __name__ == "__main__":
    import threading

    def poll():
        while True:
            try:
                bot.polling(none_stop=True)
            except Exception as e:
                logger.error(f"Bot polling failed: {e}")
                time.sleep(15)

    polling_thread = threading.Thread(target=poll)
    polling_thread.daemon = True
    polling_thread.start()

    while True:
        time.sleep(1)
