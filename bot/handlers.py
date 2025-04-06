from aiogram import Bot, types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from aiogram.dispatcher.filters import Text
from config import TOKEN
import parser_auto
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)

class BotState:
    def __init__(self):
        self.current_mark = ""
        self.current_models = []

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
bot_state = BotState()

def get_paginated_items(items: list, page: int, per_page: int = 20):
    start = page * per_page
    end = start + per_page
    return items[start:end]

@dp.message_handler(commands="start")
async def start(message: types.Message):
    """Обработчик команды /start с пагинацией марок"""
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    try:
        bot_state.current_mark = ""  # Очищаем текущую марку
        bot_state.current_models = []  # Очищаем список моделей

        msg = await message.answer("⏳ Загружаем список марок...")
        marks_dict = await parser_auto.pars_marks()
        marks = list(marks_dict.keys())

        if not marks:
            await msg.edit_text("❌ Не удалось загрузить марки автомобилей")
            return

        await send_marks_page(message, marks, page=0)
        logger.debug("Отправлен список марок (страница 0)")
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}", exc_info=True)
        await message.answer(f"⚠ Произошла ошибка: {str(e)}")

async def send_marks_page(message: types.Message, marks: list, page: int):
    per_page = 52
    total_pages = (len(marks) - 1) // per_page + 1
    current_marks = get_paginated_items(marks, page, per_page)

    markup = InlineKeyboardMarkup(row_width=4)
    for mark in current_marks:
        markup.insert(InlineKeyboardButton(text=mark, callback_data=f"mark_{mark.replace(' ', '_')}"))

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⏪ Назад", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton("⏩ Далее", callback_data=f"page_{page + 1}"))

    if navigation_buttons:
        markup.row(*navigation_buttons)

    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text("🚗 Выберите марку автомобиля:", reply_markup=markup)
    else:
        await message.answer("🚗 Выберите марку автомобиля:", reply_markup=markup)

@dp.callback_query_handler(Text(startswith="page_"))
async def navigate_pages(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    marks_dict = await parser_auto.pars_marks()
    marks = list(marks_dict.keys())
    await send_marks_page(callback, marks, page)

@dp.callback_query_handler(lambda call: call.data.startswith("mark_"))
async def handle_mark(call: types.CallbackQuery):
    """Обработчик выбора марки с полным списком моделей"""
    try:
        await call.answer("⏳ Получаем полный список моделей...")
        mark = call.data[5:].replace('_', ' ')

        bot_state.current_mark = mark
        bot_state.current_models = []  # Очищаем список перед новой загрузкой


        while True:
            models = await parser_auto.pars_model(mark)
            if models:
                break
            await asyncio.sleep(1)

        bot_state.current_models = models

        markup = InlineKeyboardMarkup(row_width=4)
        model_buttons = [InlineKeyboardButton(text=i, callback_data=f"model_{i.replace(' ', '_')}") for i in models]
        markup.add(*model_buttons)
        markup.row(InlineKeyboardButton(text="🔙 Назад к маркам", callback_data="back_to_marks"))

        await call.message.answer(f"🚘 Все модели {mark} ({len(models)}):", reply_markup=markup)

    except Exception as e:
        await call.message.answer(f"⚠ Ошибка загрузки списка моделей: {str(e)}")

@dp.callback_query_handler(lambda call: call.data == "back_to_marks")
async def back_to_marks(call: types.CallbackQuery):
    """Обработчик кнопки 'Назад'"""
    await start(call.message)

@dp.callback_query_handler(lambda call: call.data.startswith("model_"))
async def handle_model(call: types.CallbackQuery):
    """Обработчик полного списка моделей"""
    try:
        await call.answer("⏳ Ищем ВСЕ объявления...")
        model = call.data[6:].replace('_', ' ')
        mark = bot_state.current_mark
        logger.info(f"Пользователь выбрал модель: {model}")

        progress_msg = await call.message.answer(
            f"🔍 Поиск ВСЕХ объявлений для {mark} {model}...\n"
            "Это может занять несколько минут"
        )

        url = await parser_auto.get_url(model, bot_state.current_models)
        if not url:
            await progress_msg.edit_text("❌ Не удалось получить данные с сайта")
            return

        await call.message.chat.do('typing')
        auto_list = await parser_auto.pars_auto(url)

        if not auto_list:
            await progress_msg.edit_text("❌ Не найдено объявлений или ошибка при получении данных")
            return

        sent_count = 0
        limit = min(50, len(auto_list))
        for i in range(0, limit, 10):
            chunk = auto_list[i:i + 10]
            message_batch = []

            for auto in chunk:
                try:
                    params = auto['params'].split(', ')
                    message = (
                        f"🚗 <b>{auto['model']}</b>\n"
                        f"📅 {params[0] if len(params) > 0 else 'N/A'} | "
                        f"⚙ {params[1] if len(params) > 1 else 'N/A'}\n"
                        f"💰 {auto['price_byn']:,} BYN (~{auto['price_usd']:,} USD)\n"
                        f"🔗 <a href='{auto['link']}'>Подробнее</a>\n"
                    )
                    message_batch.append(message)
                except Exception as e:
                    continue

            if message_batch:
                await call.message.answer("\n\n".join(message_batch), parse_mode="HTML")
                sent_count += len(message_batch)
                await asyncio.sleep(0.5)

        await progress_msg.edit_text(
            f"✅ Найдено и отправлено {sent_count} актуальных объявлений\n"
            f"Марка: {mark}\nМодель: {model}"
        )
        logger.info(f"Отправлено {sent_count} объявлений")
    except Exception as e:
        logger.error(f"Ошибка обработки модели {model}: {e}", exc_info=True)
        await call.message.answer(f"⚠ Ошибка: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(dp.start_polling())
    except Exception as e:
        print(f"Ошибка при запуске бота: {str(e)}")