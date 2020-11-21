import logging
import logging.handlers

def get_logger():
    log_level = "DEBUG"
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger("gnd")
    logfilename = "gnd.log"

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(log_level)
    logger.addHandler(consoleHandler)

    fileHandler = logging.handlers.RotatingFileHandler(
            filename = logfilename,
            mode = "a",
            maxBytes = 10000000,
            backupCount = 3,
        )
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)
    return logger
