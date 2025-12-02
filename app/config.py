import os
from dataclasses import dataclass
from typing import List, Optional


def _parse_admins(value: Optional[str]) -> List[int]:
    if not value:
        return []
    admins: List[int] = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            admins.append(int(raw))
        except ValueError:
            continue
    return admins


@dataclass
class Settings:
    bot_token: str
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_key: Optional[str] = None
    database_path: str = "data/bot.db"
    admin_ids: Optional[List[int]] = None
    admin_panel_user_id: Optional[int] = None
    admin_panel_password: Optional[str] = None
    admin_panel_secret: Optional[str] = None
    start_photo_file_id: Optional[str] = None
    start_photo_path: Optional[str] = None

    @classmethod
    def load(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN", "")
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is required")
        api_host = os.getenv("API_HOST", "0.0.0.0")
        api_port = int(os.getenv("API_PORT", "8080"))
        api_key = os.getenv("API_KEY")
        database_path = os.getenv("DATABASE_PATH", "data/bot.db")
        admin_ids = _parse_admins(os.getenv("ADMIN_IDS"))
        admin_panel_user_id = int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
        admin_panel_password = os.getenv("ADMIN_PASSWORD")
        admin_panel_secret = os.getenv("ADMIN_SECRET")
        start_photo_file_id = os.getenv("START_PHOTO_FILE_ID")
        start_photo_path = os.getenv("START_PHOTO_PATH")
        return cls(
            bot_token=bot_token,
            api_host=api_host,
            api_port=api_port,
            api_key=api_key,
            database_path=database_path,
            admin_ids=admin_ids,
            admin_panel_user_id=admin_panel_user_id,
            admin_panel_password=admin_panel_password,
            admin_panel_secret=admin_panel_secret,
            start_photo_file_id=start_photo_file_id,
            start_photo_path=start_photo_path,
        )
