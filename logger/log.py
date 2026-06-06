import logging
import os

from pathlib import Path
from datetime import datetime



# Get dsi-offer-engine logger
log = logging.getLogger("zen chat-bot")


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Fetch the current datetime in the US timezone
        current_time = datetime.now()
        # Format it according to the provided datefmt or default to the default format
        return current_time.strftime(datefmt or self.datefmt)


def init():
    Path(f"{os.getcwd()}/logs").mkdir(parents=True, exist_ok=True)
    datetime_now = datetime.now().strftime('%Y-%m-%d')
    file_name = f"logs/{datetime_now}.log"

    file_handler = logging.FileHandler(file_name)
    formatter = CustomFormatter(
        "%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    # Ensure the specific logger uses the configuration
    log.setLevel(logging.DEBUG)
    log.addHandler(file_handler)