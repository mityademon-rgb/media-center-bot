"""
ГЛАВНЫЙ ФАЙЛ БОТА
Инициализация и запуск
"""
import os
import telebot
from handlers import (
    handle_start,
    handle_text,
    handle_callback,
    handle_photo,
    handle_stat_command,
    handle_add_event_command
)

# Токен бота (прописан прямо в коде)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8473634161:AAHv_fbBnQ37TboA9LuHCWwgLpjo66daSlA')

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

print("🤖 Бот инициализирован!")

# === ОБРАБОТЧИКИ КОМАНД ===

@bot.message_handler(commands=['start'])
def start_command(message):
    """Команда /start"""
    handle_start(bot, message)

@bot.message_handler(commands=['stat'])
def stat_command(message):
    """Команда /stat (админ)"""
    handle_stat_command(bot, message)

@bot.message_handler(commands=['add_event'])
def add_event_command(message):
    """Команда /add_event (админ)"""
    handle_add_event_command(bot, message)

# === ОБРАБОТЧИКИ КОНТЕНТА ===

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    """Обработка фото"""
    handle_photo(bot, message)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    """Обработка текста"""
    handle_text(bot, message)

# === ОБРАБОТЧИКИ CALLBACK ===

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обработка нажатий на кнопки"""
    handle_callback(bot, call)

# === ЗАПУСК БОТА ===

if __name__ == '__main__':
    print("🚀 Бот запущен и готов к работе!")
    print("=" * 50)
    
    # Запускаем планировщик
    from scheduler import start_scheduler
    start_scheduler(bot)
    
    # Polling
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
