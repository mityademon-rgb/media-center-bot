"""
ГЛАВНЫЙ ФАЙЛ БОТА
Инициализация и запуск
"""
import os
import telebot
from handlers import (
    handle_start,
    handle_callback,
    handle_message
)

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '8473634161:AAHv_fbBnQ37TboA9LuHCWwgLpjo66daSlA')

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

print("🤖 Бот инициализирован!")

# === ОБРАБОТЧИКИ КОМАНД ===

@bot.message_handler(commands=['start'])
def start_command(message):
    """Команда /start"""
    handle_start(bot, message)

# === ОБРАБОТЧИКИ КОНТЕНТА ===

@bot.message_handler(content_types=['photo', 'video', 'text'])
def message_handler(message):
    """Обработка всех сообщений"""
    handle_message(bot, message)

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
