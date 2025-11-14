"""
ГЛАВНЫЙ ФАЙЛ БОТА
Инициализация и запуск
"""
import os
import telebot
from flask import Flask, send_from_directory
import threading

from handlers import (
    handle_start,
    handle_callback,
    handle_message,
    setup_game_handlers  
)

# ============= FLASK ДЛЯ WEB APP =============

# Создаём Flask приложение
flask_app = Flask(__name__, static_folder='public', static_url_path='')

@flask_app.route('/')
def index():
    """Главная страница игр"""
    return send_from_directory('public', 'index.html')

@flask_app.route('/<path:path>')
def serve_file(path):
    """Раздача файлов из папки public"""
    return send_from_directory('public', path)

def run_flask():
    """Запуск Flask сервера"""
    port = int(os.getenv('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ============================================

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

# === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ИГР ===
setup_game_handlers(bot)

# === ЗАПУСК БОТА ===

if __name__ == '__main__':
    # Запуск Flask в отдельном потоке
    print("🌐 Запуск веб-сервера для игр...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Веб-сервер запущен на порту 5000!")
    
    print("🚀 Бот запущен и готов к работе!")
    print("=" * 50)
    
    # Запускаем планировщик
    from scheduler import start_scheduler
    start_scheduler(bot)
    
    # Polling
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
