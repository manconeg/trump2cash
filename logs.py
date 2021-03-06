# -*- coding: utf-8 -*-

from backoff import expo
from backoff import on_exception
from google.cloud import error_reporting
from google.cloud import logging
from logging import basicConfig
from logging import getLogger
from logging import NOTSET

# The format for local logs.
LOGS_FORMAT = ("%(asctime)s "
               "%(name)s "
               "%(process)d "
               "%(thread)d "
               "%(levelname)s "
               "%(message)s")

# The path to the log file for local logging.
LOG_FILE = "/tmp/trump2cash.log"


class Logs:
    """A helper for logging locally or in the cloud."""

    def __init__(self, name, to_cloud=True):
        self.to_cloud = to_cloud

        # Initialize the local file logger.
        self.local_logger = getLogger(name)
        basicConfig(format=LOGS_FORMAT, level=NOTSET, filename=LOG_FILE)

        # If requested, also initialize the Stackdriver logging and error
        # reporting clients.
        if self.to_cloud:
            self.cloud_logger = logging.Client().logger(name)
            self.error_client = error_reporting.Client()

    def debug(self, text):
        """Logs at the DEBUG level."""

        if self.to_cloud:
            self.safe_cloud_log_text(text, severity="DEBUG")
        else:
            self.local_logger.debug(text)

    def info(self, text):
        """Logs at the INFO level."""

        if self.to_cloud:
            self.safe_cloud_log_text(text, severity="INFO")
        else:
            self.local_logger.info(text)

    def warn(self, text):
        """Logs at the WARNING level."""

        if self.to_cloud:
            self.safe_cloud_log_text(text, severity="WARNING")
        else:
            self.local_logger.warning(text)

    def error(self, text):
        """Logs at the ERROR level."""

        if self.to_cloud:
            self.safe_cloud_log_text(text, severity="ERROR")
        else:
            self.local_logger.error(text)

    def catch(self, exception):
        """Logs an exception."""

        if self.to_cloud:
            self.safe_report_exception()
            self.safe_cloud_log_text(str(exception), severity="CRITICAL")
        else:
            self.local_logger.critical(str(exception))

    def safe_cloud_log_text(self, text, severity):
        """Logs to the cloud, retries if necessary, and eventually fails over
        to local logs.
        """

        try:
            self.retry_cloud_log_text(text, severity)
        except BaseException as exception:
            self.local_logger.error("Failed to log to cloud: %s %s %s" %
                                    (exception, severity, text))

    @on_exception(expo, BaseException, max_tries=7)
    def retry_cloud_log_text(self, text, severity):
        """Logs to the cloud and retries up to 7 times with exponential backoff
        if the upload fails.
        """

        self.cloud_logger.log_text(text, severity=severity)

    def safe_report_exception(self):
        """Reports the latest exception, retries if necessary, and eventually
        fails over to local logs.
        """

        try:
            self.retry_report_exception()
        except BaseException as exception:
            self.local_logger.error("Failed to report exception: %s" %
                                    exception)

    @on_exception(expo, BaseException, max_tries=7)
    def retry_report_exception(self):
        """Reports the latest exception and retries up to 7 times with
        exponential backoff if the upload fails.
        """

        self.error_client.report_exception()
