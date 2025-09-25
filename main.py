import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import logging
from dotenv import load_dotenv
import config
import os
import handlers.handlers as handlers
from handlers import create_monitor
from handlers import edit_monitor
from site_monitor import SiteMonitor
from database import Database

load_dotenv()
token = os.getenv('BOT_TOKEN')
bot = Bot(token=token)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

logging.basicConfig(
    filename=config.log_file,
    filemode="w",
    format="%(asctime)s %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.log_level),
    encoding="utf-8",
)


async def main():
    logger = logging.getLogger("main")
    logger.info("Program start")
    
    # Инициализация бд
    loop = asyncio.get_running_loop()
    db = Database(loop)
    await db.create_pool()
    await db.create_tables()
    # Инициализируем мониторинг сайтов
    monitor = SiteMonitor(bot=bot, db=db)
    bot.monitor = monitor
    try:
        # Запускаем мониторинг в фоновом режиме
        monitoring_task = asyncio.create_task(monitor.run_monitoring())

        #Запуск еженедельного отчета
        asyncio.create_task(monitor.weekly_report_task())
        # Подключаем роутер и запускаем бота
        dp.include_router(handlers.router)
        dp.include_router(create_monitor.router)
        dp.include_router(edit_monitor.router)
        logger.info("Запуск Telegram бота...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Ошибка в основном цикле: {e}")
    finally:
        # Останавливаем мониторинг
        logger.info("Остановка мониторинга...")
        #monitor.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        logger.info("Программа завершена")


if __name__ == "__main__":
    asyncio.run(main())
