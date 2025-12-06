import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./lunch_bot.db")
    ADMIN_IDS: list[int] = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
    ORDER_DEADLINE_HOUR: int = int(os.getenv("ORDER_DEADLINE_HOUR", "12"))
    ORDER_DEADLINE_MINUTE: int = int(os.getenv("ORDER_DEADLINE_MINUTE", "0"))
    DAILY_REPORT_HOUR: int = int(os.getenv("DAILY_REPORT_HOUR", "18"))
    DAILY_REPORT_MINUTE: int = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
    WEEKLY_REPORT_DAY: int = int(os.getenv("WEEKLY_REPORT_DAY", "0"))
    WEEKLY_REPORT_HOUR: int = int(os.getenv("WEEKLY_REPORT_HOUR", "18"))
    WEEKLY_REPORT_MINUTE: int = int(os.getenv("WEEKLY_REPORT_MINUTE", "0"))

settings = Settings()



