"""
Logging setup for long-running tradingmachine processes.

The one-shot jobs in this project print to standard output and let a cron wrapper redirect that into a monthly file, which is readable because each job produces one linear transcript. The market data stream does not work that way: it runs one supervisor and twenty-odd shard processes at once, so a line is only useful if it carries a timestamp, a level and the name of the process that wrote it.

This module is the whole answer to that, and it is deliberately one function rather than a logging framework. Existing modules keep their print calls.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

LOG_DIRECTORY = Path(__file__).resolve().parent.parent / "logs"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
MAXIMUM_LOG_BYTES = 100 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def configure_logging(job_name):
    """
    Set up logging for one tradingmachine process, writing to both standard error and a monthly log file.

    Standard error is where systemd and cron pick output up, and the file is what survives a journal rotation. The file is named for the job and the current month, so a process that is restarted many times in a month keeps appending to one file rather than scattering its history.

    Calling this more than once for the same job name is safe: the handlers are only attached the first time, so a module that configures logging at import and again in main does not produce every line twice.

    Args:
        job_name (str): A short name for this process, used as the logger name and in the log file name, for example "stream_zerodha_shard_07".

    Returns:
        logging.Logger: The configured logger for this job.

    Raises:
        OSError: If the logs directory cannot be created or the log file cannot be opened.
    """
    logger = logging.getLogger(job_name)
    if logger.handlers:
        return logger

    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIRECTORY / f"{job_name}_{datetime.now().strftime('%Y-%m')}.log"

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=MAXIMUM_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger
