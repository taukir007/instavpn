import io
import logging
import pastee
import sys

class PasteBinLoggingHandler(logging.StreamHandler):
    def __init__(self, *args, **kwargs):
        self.buff = io.StringIO()
        super().__init__(self.buff)

    def emit(self, record):
        super().emit(record)

        # If we hit a critical error, we'll paste and quit
        if record.levelno == logging.CRITICAL:
            url = pastee.PasteClient().paste(self.buff.getvalue())
            print("CRITICAL ERROR!")
            print(" Crash report: {}".format(url))
            print(" Support: https://github.com/sockeye44/instavpn/issues")
            sys.exit(1)

def setup_logging():
    # Get root logger and attach some formatters to it
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    pastebin_handler = PasteBinLoggingHandler()
    pastebin_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S')

    console_handler.setFormatter(formatter)
    pastebin_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(pastebin_handler)

# Example usage:
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger()
    logger.info("This is an info message.")
    logger.critical("This is a critical message.")
