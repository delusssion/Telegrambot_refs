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


def _parse_single_int(value: Optional[str]) -> Optional[int]:
    """Возвращает первое целое из строки с числами через запятую/пробел или None."""
    if not value:
        return None
    for raw in value.replace(" ", "").split(","):
        if not raw:
            continue
        try:
            return int(raw)
        except ValueError:
            continue
    return None


def _parse_admin_credentials(value: Optional[str]) -> List[tuple]:
    """
    Парсит пары логин:пароль, разделённые запятыми или точкой с запятой.
    Пример: "123:pass1,456:pass2".
    """
    if not value:
        return []
    creds: List[tuple] = []
    for raw in value.replace(";", ",").split(","):
        raw = raw.strip()
        if not raw:
            continue
        if ":" not in raw:
            continue
        login, pwd = raw.split(":", 1)
        login = login.strip()
        pwd = pwd.strip()
        if not login or not pwd:
            continue
        creds.append((login, pwd))
    return creds


@dataclass
class Settings:
    bot_token: str
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_key: Optional[str] = None
    database_path: str = "data/bot.db"
    admin_ids: Optional[List[int]] = None
    admin_panel_user_id: Optional[int] = None  # legacy: одиночный логин
    admin_panel_password: Optional[str] = None  # legacy: одиночный пароль
    admin_credentials: Optional[List[tuple]] = None  # список пар логин/пароль
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
        admin_panel_user_id = _parse_single_int(os.getenv("ADMIN_USER_ID"))
        admin_panel_password = os.getenv("ADMIN_PASSWORD")
        admin_credentials = _parse_admin_credentials(os.getenv("ADMIN_USERS"))
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
            admin_credentials=admin_credentials,
            admin_panel_secret=admin_panel_secret,
            start_photo_file_id=start_photo_file_id,
            start_photo_path=start_photo_path,
        )
