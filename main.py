from aiogram import Bot, Dispatcher, executor
from bot.handlers import register_handlers
from bot.config import TOKEN
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

register_handlers(dp)

if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logger.critical(f"Бот упал с ошибкой: {e}", exc_info=True)
    finally:
        logger.info("Бот остановлен")