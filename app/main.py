import asyncio

import uvicorn
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .api import create_api
from .bot import setup_bot
from .config import Settings
from .db import Database


async def run_bot(bot: Bot, settings: Settings, database: Database) -> None:
    dispatcher = setup_bot(settings, database)
    await dispatcher.start_polling(bot)


async def run_api(settings: Settings, database: Database) -> None:
    app = create_api(settings, database)
    config = uvicorn.Config(
        app=app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    settings = Settings.load()
    database = Database(settings.database_path)
    await database.init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    await asyncio.gather(
        run_bot(bot, settings, database),
        run_api(settings, database),
    )


if __name__ == "__main__":
    asyncio.run(main())
