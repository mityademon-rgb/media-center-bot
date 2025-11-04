"""
Главный файл бота
"""
import telebot
from config import TELEGRAM_TOKEN
from handlers import handle_start, handle_text, handle_callback, handle_photo
from scheduler import start_scheduler

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Регистрация обработчиков
@bot.message_handler(commands=['start'])
def start(message):
    handle_start(bot, message)

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    handle_photo(bot, message)

@bot.message_handler(func=lambda m: True)
def text_handler(message):
    handle_text(bot, message)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    handle_callback(bot, call)

# Запуск бота
if __name__ == '__main__':
    print("✅ Бот запущен!")
    
    # Запускаем планировщик напоминаний
    start_scheduler(bot)
    
    bot.polling(none_stop=True)
