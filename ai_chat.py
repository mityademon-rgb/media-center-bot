"""
AI-чат с YandexGPT
"""
import telebot
from yandex_gpt import ask_yandex_gpt
from keyboards import back_to_menu_keyboard

# История диалогов (в памяти)
user_conversations = {}

def handle_ai_chat_menu(bot, message):
    """Главное меню AI-чата"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    buttons = [
        telebot.types.InlineKeyboardButton("💬 Задать вопрос", callback_data="ai_ask"),
        telebot.types.InlineKeyboardButton("🎥 Про съёмку", callback_data="ai_camera"),
        telebot.types.InlineKeyboardButton("✍️ Про журналистику", callback_data="ai_journalism"),
        telebot.types.InlineKeyboardButton("🗑️ Очистить историю", callback_data="ai_clear"),
        telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    ]
    
    markup.add(*buttons)
    
    text = """
🤖 **AI-ПОМОЩНИК МЕДИАЦЕНТРА**

Задай любой вопрос про:
• Съёмку видео и работу с камерой
• Журналистику и интервью
• Монтаж и контент

Просто напиши свой вопрос!
"""
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')


def handle_ai_question(bot, message):
    """Обработка вопроса пользователя"""
    user_id = message.from_id
    question = message.text
    
    # Показываем что бот думает
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Получаем ответ от YandexGPT
    answer = ask_yandex_gpt(question)
    
    # Сохраняем в историю
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    user_conversations[user_id].append({
        'question': question,
        'answer': answer
    })
    
    # Оставляем только последние 10 сообщений
    if len(user_conversations[user_id]) > 10:
        user_conversations[user_id] = user_conversations[user_id][-10:]
    
    # Отправляем ответ
    bot.send_message(
        message.chat.id,
        f"🤖 **Ответ:**\n\n{answer}",
        parse_mode='Markdown',
        reply_markup=back_to_menu_keyboard()
    )


def handle_ai_camera(bot, call):
    """Быстрые вопросы про съёмку"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    questions = [
        ("🏠 Как снимать в помещении?", "ai_q_indoor"),
        ("🌤️ Как снимать на улице?", "ai_q_outdoor"),
        ("🎤 Как снимать интервью?", "ai_q_interview"),
        ("🎭 Как снимать концерт?", "ai_q_concert"),
    ]
    
    for text, callback in questions:
        markup.add(telebot.types.InlineKeyboardButton(text, callback_data=callback))
    
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="ai_menu"))
    
    bot.edit_message_text(
        "🎥 **ВОПРОСЫ ПРО СЪЁМКУ**\n\nВыбери тему:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def handle_ai_journalism(bot, call):
    """Быстрые вопросы про журналистику"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    questions = [
        ("💬 Как разговорить собеседника?", "ai_j_conversation"),
        ("🎤 Как брать интервью?", "ai_j_interview"),
        ("❓ Какие вопросы задавать?", "ai_j_questions"),
        ("📋 Как подготовиться?", "ai_j_prep"),
    ]
    
    for text, callback in questions:
        markup.add(telebot.types.InlineKeyboardButton(text, callback_data=callback))
    
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="ai_menu"))
    
    bot.edit_message_text(
        "✍️ **ВОПРОСЫ ПРО ЖУРНАЛИСТИКУ**\n\nВыбери тему:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def handle_predefined_question(bot, call, question):
    """Обработка готовых вопросов"""
    bot.answer_callback_query(call.id, "Думаю... 🤔")
    bot.send_chat_action(call.message.chat.id, 'typing')
    
    answer = ask_yandex_gpt(question)
    
    bot.send_message(
        call.message.chat.id,
        f"❓ **Вопрос:** {question}\n\n🤖 **Ответ:**\n\n{answer}",
        parse_mode='Markdown',
        reply_markup=back_to_menu_keyboard()
    )


def handle_ai_clear(bot, call):
    """Очистка истории диалога"""
    user_id = call.from_user.id
    
    if user_id in user_conversations:
        del user_conversations[user_id]
    
    bot.answer_callback_query(call.id, "✅ История очищена!")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="ai_menu"))
    
    bot.edit_message_text(
        "🗑️ История диалога очищена!\n\nМожешь начать новый разговор.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
