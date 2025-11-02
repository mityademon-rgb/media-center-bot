import telebot
import os

# Токен бота
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

print("🚀 Бот запускается...")

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎬 Йо! Я бот медиацентра Марфино!\n\n"
        "Это базовая версия. Скоро будут крутые фичи!\n\n"
        "Напиши что-нибудь, и я отвечу! 🚀"
    )

# Ответ на текст
@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.send_message(
        message.chat.id,
        f"Ты написал: {message.text}\n\n"
        "Пока я простой, но скоро стану умнее! 🤖"
    )

# Запуск
if __name__ == '__main__':
    print("✅ Бот запущен и готов к работе!")
    bot.polling(none_stop=True)
