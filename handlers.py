"""
Обработчики команд и кнопок
"""
from keyboards import main_menu, cheatsheets_menu, links_menu, tests_menu
from texts import WELCOME_TEXT, CHEATSHEETS
from database import is_registered, get_user, get_user_display_name
from registration import start_registration, handle_registration_step, handle_qr_code
from admin import handle_stat

# ========== КОМАНДА /START ==========
def handle_start(bot, message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # НОВЫЙ ПОЛЬЗОВАТЕЛЬ - начинаем регистрацию
    if not user:
        start_registration(bot, message)
        return
    
    # ПРОВЕРЯЕМ ШАГ РЕГИСТРАЦИИ
    reg_step = user.get('registration_step', 999)
    
    # Если пользователь в процессе регистрации (шаги 1-4)
    if reg_step < 5:
        bot.send_message(
            user_id,
            "⚠️ Эй, ты ещё не закончил регистрацию!\n\n"
            "Продолжай отвечать на мои вопросы 👆"
        )
        return
    
    # Если ожидает QR-код (шаг 5)
    if reg_step == 5 and not user.get('qr_code'):
        display_name = get_user_display_name(user_id)
        bot.send_message(
            user_id,
            f"Йоу, {display_name}! 👋\n\n"
            f"Я жду твой QR-код с портала МосРег 📸\n\n"
            f"Скинь мне фото или скрин бейджа, "
            f"и мы сможем продолжить!\n\n"
            f"А пока можешь юзать бота 👇",
            reply_markup=main_menu()
        )
        return
    
    # ПОЛЬЗОВАТЕЛЬ ЗАРЕГИСТРИРОВАН - показываем главное меню
    display_name = get_user_display_name(user_id)
    bot.send_message(
        message.chat.id,
        f"🎬 Йоу, {display_name}! Рад тебя видеть! 🔥\n\n"
        f"Что будем делать?",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
def handle_text(bot, message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # ЕСЛИ ПОЛЬЗОВАТЕЛЯ НЕТ В БАЗЕ - начинаем регистрацию
    if not user:
        start_registration(bot, message)
        return
    
    # ПРОВЕРЯЕМ ШАГ РЕГИСТРАЦИИ
    reg_step = user.get('registration_step', 999)
    
    # ЕСЛИ В ПРОЦЕССЕ РЕГИСТРАЦИИ (шаги 1-4)
    if reg_step < 5:
        handle_registration_step(bot, message)
        return
    
    # ЕСЛИ ОЖИДАЕТ QR-КОД (шаг 5) и прислал фото
    if reg_step == 5 and not user.get('qr_code'):
        if message.content_type == 'photo':
            handle_qr_code(bot, message)
            return
        else:
            # Напоминаем про QR-код
            bot.send_message(
                user_id,
                "📸 Не забудь скинуть мне QR-код с бейджа!\n\n"
                "А пока можешь юзать бота 👇",
                reply_markup=main_menu()
            )
            return
    
    # ОБЫЧНАЯ ОБРАБОТКА СООБЩЕНИЙ (пользователь зарегистрирован)
    text = message.text
    
    if text == '📚 Шпаргалки':
        bot.send_message(
            message.chat.id,
            "📚 *ШПАРГАЛКИ*\n\nВыбирай тему! 👇",
            parse_mode='Markdown',
            reply_markup=cheatsheets_menu()
        )
    
    elif text == '🔗 Полезные ссылки':
        bot.send_message(
            message.chat.id,
            "🔗 *ПОЛЕЗНЫЕ ССЫЛКИ*\n\nКуда хочешь заглянуть? 👇",
            parse_mode='Markdown',
            reply_markup=links_menu()
        )
    
    elif text == '🎯 Тесты':
        bot.send_message(
            message.chat.id,
            "🎯 *ТЕСТЫ*\n\nПроверь свои знания! 👇",
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
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "🏠 *Главное меню*\n\nВыбирай! 👇",
            parse_mode='Markdown',
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
        bot.answer_callback_query(call.id, "🎥 Тест скоро будет! Следи за обновами 😉")
    
    elif call.data == 'test_journalism':
        bot.answer_callback_query(call.id, "📰 Тест скоро будет! Следи за обновами 😉")
    
    elif call.data == 'test_directing':
        bot.answer_callback_query(call.id, "🎬 Тест скоро будет! Следи за обновами 😉")

# ========== ОБРАБОТКА ФОТО (для QR-кода) ==========
def handle_photo(bot, message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # ЕСЛИ НЕТ ПОЛЬЗОВАТЕЛЯ - начинаем регистрацию
    if not user:
        start_registration(bot, message)
        return
    
    # ЕСЛИ ОЖИДАЕМ QR-КОД
    if user.get('registration_step') == 5 and not user.get('qr_code'):
        handle_qr_code(bot, message)
    else:
        bot.send_message(user_id, "🤔 Зачем фото? Используй кнопки меню 👇", reply_markup=main_menu())

# ========== КОМАНДА /STAT (для админа) ==========
def handle_stat_command(bot, message):
    handle_stat(bot, message)
