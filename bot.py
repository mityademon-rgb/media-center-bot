import telebot
from telebot.types import ReplyKeyboardRemove
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    # Убираем старые кнопки
    bot.send_message(
        message.chat.id, 
        "🎬 Привет! Я бот медиацентра Марфино!\n\n"
        "Это обновлённая версия. Старые кнопки убраны!\n\n"
        "Пиши команды:\n"
        "/start - начать\n"
        "/help - помощь",
        reply_markup=ReplyKeyboardRemove()
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "📚 Доступные команды:\n\n"
        "/start - начать заново\n"
        "/help - эта справка"
    )

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.send_message(
        message.chat.id, 
        f"✉️ Ты написал: {message.text}\n\n"
        "Скоро добавим больше функций! 🚀"
    )

if __name__ == '__main__':
    print("✅ Бот запущен!")
    bot.polling(none_stop=True)
