"""
Обработчики команд и кнопок
"""
from keyboards import main_menu, cheatsheets_menu, links_menu, tests_menu
from texts import WELCOME_TEXT, CHEATSHEETS

# ========== КОМАНДА /START ==========
def handle_start(bot, message):
    bot.send_message(
        message.chat.id,
        WELCOME_TEXT,
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
def handle_text(bot, message):
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
