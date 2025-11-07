"""
AI-чат с OpenAI GPT
"""
import telebot
from openai_gpt import ask_gpt, ask_gpt_with_context  # ← ИЗМЕНИЛИ ЭТУ СТРОКУ
from keyboards import back_to_menu_keyboard

# История диалогов (в памяти, по user_id)
user_conversations = {}

# Режим ожидания вопроса
waiting_for_question = set()


def handle_ai_chat_menu(bot, message):
    """Главное меню AI-чата"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    user_id = message.from_user.id
    has_history = user_id in user_conversations and len(user_conversations[user_id]) > 0
    
    buttons = [
        telebot.types.InlineKeyboardButton("💬 Задать вопрос", callback_data="ai_ask"),
        telebot.types.InlineKeyboardButton("🎥 Про съёмку", callback_data="ai_camera"),
        telebot.types.InlineKeyboardButton("✍️ Про журналистику", callback_data="ai_journalism"),
    ]
    
    if has_history:
        buttons.append(telebot.types.InlineKeyboardButton("🗑️ Очистить историю", callback_data="ai_clear"))
    
    buttons.append(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    
    markup.add(*buttons)
    
    history_text = ""
    if has_history:
        count = len(user_conversations[user_id])
        history_text = f"\n\n📚 В истории: {count} диалог(ов)"
    
    text = f"""
🤖 **AI-ПОМОЩНИК МЕДИАЦЕНТРА**

Задай любой вопрос про:
• 🎥 Съёмку видео и работу с камерой
• ✍️ Журналистику и интервью
• 🎬 Монтаж и производство контента

Просто напиши свой вопрос или выбери тему!{history_text}
"""
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')


def handle_ai_ask(bot, call):
    """Активировать режим ожидания вопроса"""
    user_id = call.from_user.id
    waiting_for_question.add(user_id)
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("❌ Отмена", callback_data="ai_menu"))
    
    bot.edit_message_text(
        "💬 **Напиши свой вопрос:**\n\nЯ отвечу на любой вопрос про съёмку, журналистику или создание контента!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def handle_ai_question(bot, message):
    """Обработка вопроса пользователя"""
    user_id = message.from_user.id
    question = message.text
    
    # Проверяем что пользователь в режиме вопроса
    if user_id not in waiting_for_question:
        return
    
    # Убираем из режима ожидания
    waiting_for_question.discard(user_id)
    
    # Показываем что бот думает
    thinking_msg = bot.send_message(message.chat.id, "🤔 Думаю...")
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Получаем историю
    history = user_conversations.get(user_id, [])
    
    # Получаем ответ от YandexGPT
    if history:
        answer = ask_with_context(question, history)
    else:
        answer = ask_yandex_gpt(question)
    
    # Удаляем сообщение "Думаю..."
    try:
        bot.delete_message(message.chat.id, thinking_msg.message_id)
    except:
        pass
    
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
    
    # Кнопки после ответа
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("💬 Ещё вопрос", callback_data="ai_ask"),
        telebot.types.InlineKeyboardButton("◀️ Меню", callback_data="ai_menu")
    )
    
    # Отправляем ответ
    bot.send_message(
        message.chat.id,
        f"❓ **Твой вопрос:**\n{question}\n\n🤖 **Ответ:**\n\n{answer}",
        parse_mode='Markdown',
        reply_markup=markup
    )


def handle_ai_camera(bot, call):
    """Быстрые вопросы про съёмку"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    questions = [
        ("🏠 Как снимать в помещении?", "ai_q_indoor"),
        ("🌤️ Как снимать на улице?", "ai_q_outdoor"),
        ("🎤 Как снимать интервью?", "ai_q_interview"),
        ("🎭 Как снимать концерт?", "ai_q_concert"),
        ("💡 Как работать со светом?", "ai_q_light"),
    ]
    
    for text, callback in questions:
        markup.add(telebot.types.InlineKeyboardButton(text, callback_data=callback))
    
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="ai_menu"))
    
    bot.edit_message_text(
        "🎥 **ВОПРОСЫ ПРО СЪЁМКУ**\n\nВыбери тему или задай свой вопрос:",
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
        ("📋 Как подготовиться к интервью?", "ai_j_prep"),
        ("✍️ Как писать закадровый текст?", "ai_j_voiceover"),
    ]
    
    for text, callback in questions:
        markup.add(telebot.types.InlineKeyboardButton(text, callback_data=callback))
    
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="ai_menu"))
    
    bot.edit_message_text(
        "✍️ **ВОПРОСЫ ПРО ЖУРНАЛИСТИКУ**\n\nВыбери тему или задай свой вопрос:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


# Готовые вопросы
PREDEFINED_QUESTIONS = {
    # Съёмка
    'ai_q_indoor': "Как правильно снимать видео в помещении? Расскажи про свет, настройки камеры и композицию.",
    'ai_q_outdoor': "Как снимать видео на улице? Как работать с естественным светом и погодой?",
    'ai_q_interview': "Как правильно снимать интервью? Ракурсы, композиция, звук.",
    'ai_q_concert': "Как снимать концерт или живое выступление? Что важно учесть?",
    'ai_q_light': "Как работать со светом при съёмке? Естественный и искусственный свет.",
    
    # Журналистика
    'ai_j_conversation': "Как разговорить собеседника и получить интересные ответы в интервью?",
    'ai_j_interview': "Как правильно брать интервью? Подготовка, ведение, финал.",
    'ai_j_questions': "Какие вопросы задавать в интервью? Приведи примеры хороших вопросов.",
    'ai_j_prep': "Как подготовиться к интервью? Что нужно узнать заранее?",
    'ai_j_voiceover': "Как писать хороший закадровый текст для видео? Дай советы и примеры.",
}


def handle_predefined_question(bot, call):
    """Обработка готовых вопросов"""
    question_id = call.data
    question = PREDEFINED_QUESTIONS.get(question_id)
    
    if not question:
        bot.answer_callback_query(call.id, "❌ Вопрос не найден")
        return
    
    bot.answer_callback_query(call.id, "🤔 Думаю...")
    
    # Показываем что думаем
    bot.edit_message_text(
        f"❓ **Вопрос:** {question}\n\n🤖 Думаю...",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    bot.send_chat_action(call.message.chat.id, 'typing')
    
    # Получаем ответ
    answer = ask_yandex_gpt(question)
    
    # Сохраняем в историю
    user_id = call.from_user.id
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    user_conversations[user_id].append({
        'question': question,
        'answer': answer
    })
    
    if len(user_conversations[user_id]) > 10:
        user_conversations[user_id] = user_conversations[user_id][-10:]
    
    # Кнопки
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("💬 Свой вопрос", callback_data="ai_ask"),
        telebot.types.InlineKeyboardButton("◀️ Меню", callback_data="ai_menu")
    )
    
    # Отправляем ответ
    bot.edit_message_text(
        f"❓ **Вопрос:**\n{question}\n\n🤖 **Ответ:**\n\n{answer}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
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
        "🗑️ **История диалога очищена!**\n\nМожешь начать новый разговор.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
