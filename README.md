# 🚗 Telegram Авто-Парсер Бот

Этот бот помогает быстро найти свежие объявления о продаже популярных моделей автомобилей с сайта [cars.av.by](https://cars.av.by).

## 🌟 Возможности
- 🔍 **Парсинг объявлений** с av.by в реальном времени
- 🚀 **Асинхронная работа** — не блокирует других пользователей
- 📱 **Удобное меню** с кнопками выбора марки/модели
- 📊 **Логирование** всех действий

## 🛠 Установка и запуск

1. Клонируй репозиторий:
```bash
git clone https://github.com/yourusername/auto-telegram-bot.git
cd auto-telegram-bot.

2. Установка зависимостей:
pip install -r requirements.txt.

3. Настройка окружения:
  Создайте файл .env в папке bot/:
    TOKEN=ваш_токен_бота
    CHROME_DRIVER_PATH=путь/к/chromedriver  # или оставьте пустым для автоустановки
  Для Windows скачайте ChromeDriver и укажите путь.

4. Запуск:
  python main.py.

## ⚙️ Техническая информация
- **Стек технологий**:
  - Python 3.9+
  - Aiogram (Telegram Bot API)
  - Selenium (парсинг JS-страниц)
  - BeautifulSoup4 (разбор HTML)
- **Архитектура**:
  - Асинхронная модель (asyncio)
  - Разделение на модули (парсер, бот, конфиг)

