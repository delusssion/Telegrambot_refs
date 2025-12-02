from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import Settings
from .db import Database
from .admin_routes import build_admin_router
from .public_routes import build_public_router


def create_api(settings: Settings, database: Database) -> FastAPI:
    app = FastAPI(title="ReferralBot Backend", version="0.1.0")

    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    admin_panel_dir = static_dir / "admin_panel"
    admin_panel_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/admin_panel/static", StaticFiles(directory=admin_panel_dir), name="admin_panel_static")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    app.include_router(build_public_router())
    app.include_router(build_admin_router(settings, database, bot, static_dir, admin_panel_dir))

    return app
