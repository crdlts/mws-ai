# report_injestor/app/config.py
import os


class Settings:
    def __init__(self) -> None:
        # включать/выключать debug через переменную окружения
        self.DEBUG = os.getenv("REPORT_INJESTOR_DEBUG", "false").lower() == "true"
        self.PROJECT_NAME = os.getenv("REPORT_INJESTOR_PROJECT_NAME", "report_injestor")


settings = Settings()

