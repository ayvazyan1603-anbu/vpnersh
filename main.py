import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для корректного импорта модулей в Docker/Linux
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database.db as db
from handlers import main_router
from webapp_api import start_webapp_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не задан в конфигурации или .env файле!")
        return

    # Инициализация базы данных
    logger.info("Инициализация базы данных SQLite...")
    await db.init_db()

    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Запускаем WebApp API и Webhook сервер
    logger.info("Запуск WebApp API сервера...")
    await start_webapp_server(bot=bot)

    # Регистрация роутеров
    dp.include_router(main_router)

    # Получаем информацию о боте и сохраняем username
    bot_info = await bot.get_me()
    config.BOT_USERNAME = bot_info.username or ""

    # Установка кнопки меню слева от поля ввода (как на скриншоте "Cabinet")
    if getattr(config, 'WEBAPP_URL', ''):
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            webapp_full_url = f"{config.WEBAPP_URL.rstrip('/')}/webapp/index.html"
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Cabinet",
                    web_app=WebAppInfo(url=webapp_full_url)
                )
            )
            logger.info(f"Кнопка 'Cabinet' успешно установлена: {webapp_full_url}")
        except Exception as e:
            logger.error(f"Ошибка при установке кнопки меню: {e}")

    webapp_port = config.WEBAPP_PORT if hasattr(config, 'WEBAPP_PORT') else 8443
    logger.info(f"Бот @{bot_info.username} успешно запущен!")
    print("=" * 50)
    print(f"🚀 VPN Бот @{bot_info.username} запущен и готов к работе!")
    print(f"🌐 WebApp API: http://0.0.0.0:{webapp_port}/webapp/index.html")
    print("=" * 50)

    try:
        # Пропуск накопившихся апдейтов при перезапуске
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен пользователем.")
