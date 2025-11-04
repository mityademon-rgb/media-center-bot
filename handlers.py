"""
Обработчики команд и кнопок
"""
from keyboards import main_menu, cheatsheets_menu, links_menu, tests_menu
from texts import WELCOME_TEXT, CHEATSHEETS
from database import is_registered, get_user, get_user_display_name
from registration import start_registration, handle_registration_step, handle_qr_code

# ========== КОМАНДА /START ==========
def handle_start(bot, message):
    user_id = message.chat.id
    
    # Проверяем регистрацию
    if not is_registered(user_id):
        user = get_user(user_id)
        
        # Если пользователь в процессе регистрации
        if user and user.get('registration_step', 1) < 5:
            bot.send_message(
                user_id,
                "⚠️ Ты ещё не завершил регистрацию!\n\n"
                "Продолжай отвечать на вопросы 👆"
            )
            return
        
        # Если ожидает QR-код
        if user and user.get('registration_step') == 5:
            display_name = get_user_display_name(user_id)
            bot.send_message(
                user_id,
                f"👋 {display_name}!\n\n"
                f"Я жду твой QR-код с портала МосРег 📸\n\n"
                f"Пришли мне фото или скриншот кода, "
                f"и мы сможем продолжить!\n\n"
                f"Пока можешь пользоваться ботом 👇",
                reply_markup=main_menu()
            )
            return
        
        # Новый пользователь - начинаем регистрацию
        start_registration(bot, message)
        return
    
    # Пользователь зарегистрирован - показываем главное меню
    display_name = get_user_display_name(user_id)
    bot.send_message(
        message.chat.id,
        f"🎬 Привет, {display_name}!\n\n{WELCOME_TEXT}",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
def handle_text(bot, message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # Если пользователь в процессе регистрации
    if user and user.get('registration_step', 999) < 5:
        handle_registration_step(bot, message)
        return
    
    # Если ожидаем QR-код (любое фото сохраняем)
    if user and user.get('registration_step') == 5 and not user.get('qr_code'):
        if message.photo:
            handle_qr_code(bot, message)
            return
    
    # Обычная обработка сообщений
    text = message.text
    
    if text == '📚 Шпаргалки':
        bot.send_message(
            message.chat.id,
            "📚 *ШПАРГАЛКИ*\n\nВыбери тему:",
            parse_mode='Markdown',
            reply_markup=cheatsheets_menu()
        )
    
    elif text == '🔗 Полезные ссылки':
        bot.send_message(
            message.chat.id,
            "🔗 *ПОЛЕЗНЫЕ ССЫЛКИ*\n\nВыбери ресурс:",
            parse_mode='Markdown',
            reply_markup=links_menu()
        )
    
    elif text == '🎯 Тесты':
        bot.send_message(
            message.chat.id,
            "🎯 *ТЕСТЫ*\n\nВыбери тест:",
            parse_mode='Markdown',
            reply_markup=tests_menu()
        )
    
    else:
        bot.send_message(
            message.chat.id,
            "Используй кнопки меню 👇"
        )

# ========== ОБРАБОТКА CALLBACK КНОПОК ==========
def handle_callback(bot, call):
    
    # Главное меню
    if call.data == 'main_menu':
        bot.edit_message_text(
            "🏠 *Главное меню*\n\nВыбери раздел:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.send_message(
            call.message.chat.id,
            "Выбери раздел:",
            reply_markup=main_menu()
        )
    
    # Шпаргалки
    elif call.data in CHEATSHEETS:
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            CHEATSHEETS[call.data],
            parse_mode='Markdown'
        )
    
    # Тесты (пока заглушки)
    elif call.data == 'test_camera':
        bot.answer_callback_query(call.id, "🎥 Тест скоро будет добавлен!")
    
    elif call.data == 'test_journalism':
        bot.answer_callback_query(call.id, "📰 Тест скоро будет добавлен!")
    
    elif call.data == 'test_directing':
        bot.answer_callback_query(call.id, "🎬 Тест скоро будет добавлен!")

# ========== ОБРАБОТКА ФОТО (для QR-кода) ==========
def handle_photo(bot, message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # Если ожидаем QR-код
    if user and user.get('registration_step') == 5 and not user.get('qr_code'):
        handle_qr_code(bot, message)
    else:
        bot.send_message(user_id, "🤔 Зачем ты прислал фото? Используй кнопки меню 👇")
