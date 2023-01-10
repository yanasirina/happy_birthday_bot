from loggers.tg_logger import TgLogger
from loggers.google_sheets_logger import GoogleSheetsLogger


class Logger:
    def __init__(self, tg_logger: TgLogger, google_sheets_logger: GoogleSheetsLogger):
        self.tg = tg_logger
        self.sheets = google_sheets_logger
