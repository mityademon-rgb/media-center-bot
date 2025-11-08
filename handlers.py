"""
РОУТЕР КОМАНД И СООБЩЕНИЙ
Направляет запросы в соответствующие блоки
"""
from ai_chat import (
    handle_ai_chat_menu, handle_ai_ask, handle_ai_question,
    handle_ai_camera, handle_ai_journalism, handle_predefined_question,
    handle_ai_clear, waiting_for_question
)

from database import get_user, is_registered, update_user, get_user_display_name
from registration import (
    handle_start_registration,
    handle_registration_step,
    handle_nickname_preference,
    handle_qr_photo
)
from admin import handle_stat, handle_export_db, handle_without_qr, is_admin

# ИМПОРТЫ РАСПИСАНИЯ УБРАНЫ! Теперь импортируем лениво внутри функций

from keyboards import main_reply_keyboard, main_menu_keyboard, schedule_keyboard

# ============ ИМПОРТЫ ЗАДАНИЙ ============
from tasks import (
    handle_tasks_menu,
    handle_available_tasks,
    handle_task_view,
    handle_task_submit,
    handle_task_approve,
    handle_task_reject,
    handle_completed_tasks,
    handle_tasks_progress,
    handle_tasks_help,
    handle_task_submission,
    waiting_for_task_submission
)

def handle_start(bot, message):
    """Команда /start"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Если пользователя нет или регистрация не завершена
    if not user or not is_registered(user_id):
        return handle_start_registration(bot, message)
    
    # Обновляем активность
    update_user(user_id, {})


    # Показываем главное меню с постоянной клавиатурой
    display_name = get_user_display_name(user_id)
    
    welcome_text = f"""
Йоу, {display_name}! 👋

Рад тебя видеть! Чем могу помочь?
"""
    
    keyboard = main_reply_keyboard()  # Постоянная клавиатура внизу!
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=keyboard
    )

def handle_message(bot, message):
    """Обработка текстовых сообщений"""
    
    user_id = message.from_user.id
    text = message.text
    
    # Команда /ras для добавления занятия (только админ)
    if text and text.startswith('/ras'):
        from admin import is_admin
        if is_admin(user_id):
            from schedule_module import handle_add_event_start
            return handle_add_event_start(bot, message)
        else:
            bot.send_message(message.chat.id, "⛔ Доступ запрещён!")
            return
    
    # Проверяем комментарий от админа
    from tasks import handle_admin_comment
    if handle_admin_comment(bot, message):
        return
    
    # Проверяем отправку задания
    from tasks import handle_task_submission
    if handle_task_submission(bot, message):
        return
    
    user = get_user(user_id)
    
    # Проверяем добавление события (ВАЖНО: до регистрации!)
    if user and user.get('adding_event'):
        from schedule_module import handle_add_event_step
        return handle_add_event_step(bot, message)
    
    # Если регистрация не завершена - направляем в регистрацию
    if not user or not is_registered(user_id):
        return handle_registration_step(bot, message)
    
    # Проверка на вопросы AI
    if user_id in waiting_for_question:
        return handle_ai_question(bot, message)
    
    # ============ ПРОВЕРКА ОТПРАВКИ ЗАДАНИЯ ============
    if user_id in waiting_for_task_submission:
        if handle_task_submission(bot, message):
            return
    
    # Обновляем активность
    update_user(user_id, {})
    
    text = message.text
    
    # AI-Помощник
    if text == "🤖 AI-Помощник":
        handle_ai_chat_menu(bot, message)
        return
    
    # Расписание
    if text == "📅 Расписание":
        keyboard = schedule_keyboard()
        bot.send_message(
            message.chat.id,
            "📅 **РАСПИСАНИЕ МЕДИАЦЕНТРА**\n\n"
            "Выбери что хочешь посмотреть:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # ============ ЗАДАНИЯ ============
    if text == "🎯 Задания":
        handle_tasks_menu(bot, message)
        return
    
    # Профиль
    if text == "👤 Профиль":
        display_name = get_user_display_name(user_id)
        profile_text = f"""
👤 **Твой профиль:**

• Имя: {user.get('first_name', '—')} {user.get('last_name', '—')}
• Никнейм: {user.get('nickname', '—')}
• Возраст: {user.get('age', '—')}
• QR-код: {'✅ Загружен' if user.get('qr_code') else '⏳ Не загружен'}

📊 Уровень: {user.get('level', 1)}
⭐ XP: {user.get('xp', 0)}
"""
        bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')
        return
    
    # Прогресс
    if text == "📊 Прогресс":
        bot.send_message(
            message.chat.id,
            f"📊 **Твой прогресс:**\n\n"
            f"⭐ Уровень: {user.get('level', 1)}\n"
            f"💎 XP: {user.get('xp', 0)}\n"
            f"✅ Заданий выполнено: {user.get('tasks_completed', 0)}\n\n"
            f"Продолжай в том же духе! 🚀",
            parse_mode='Markdown'
        )
        return
    
    # Помощь
    if text == "❓ Помощь":
        help_text = """
❓ **ПОМОЩЬ**

**Что я умею:**

📅 **Расписание** - все занятия медиацентра
🎯 **Задания** - творческие задачи с наградами
👤 **Профиль** - твои данные и прогресс
📊 **Прогресс** - уровень и достижения
🤖 **AI-Помощник** - задай любой вопрос

**Команды:**
/start - главное меню
/stat - статистика (только для админа)
/ras - добавить занятие (только для админа)

Возникли вопросы? Пиши @mityademonrgb 💬
"""
        bot.send_message(message.chat.id, help_text, parse_mode='Markdown')
        return
    
    # Если команда не распознана
    if text.lower() in ['меню', 'главное меню', '/menu']:
        return handle_start(bot, message)
    
    bot.send_message(
        message.chat.id,
        "🤔 Не совсем понял... Используй кнопки внизу! 👇\n\n"
        "Или напиши /start для главного меню"
    )

def handle_callback(bot, call):
    """Обработка нажатий на inline кнопки"""
    user_id = call.from_user.id
    data = call.data
    
    # Обновляем активность
    update_user(user_id, {})
    
    # AI-ЧАТ
    if data == "ai_menu":
        handle_ai_chat_menu(bot, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "ai_ask":
        handle_ai_ask(bot, call)
        return
    
    if data == "ai_camera":
        handle_ai_camera(bot, call)
        return
    
    if data == "ai_journalism":
        handle_ai_journalism(bot, call)
        return
    
    if data == "ai_clear":
        handle_ai_clear(bot, call)
        return
    
    if data.startswith("ai_q_") or data.startswith("ai_j_"):
        handle_predefined_question(bot, call)
        return
    
    # ============ ЗАДАНИЯ ============
    if data == "tasks_menu":
        handle_tasks_menu(bot, call.message)
        bot.answer_callback_query(call.id)
        return
    
    if data == "tasks_available":
        handle_available_tasks(bot, call)
        return
    
    if data.startswith("task_view_"):
        handle_task_view(bot, call)
        return
    
    if data.startswith("task_submit_"):
        handle_task_submit(bot, call)
        return
    
    if data.startswith("approve_"):
        handle_task_approve(bot, call)
        return
    
    if data.startswith("reject_"):
        handle_task_reject(bot, call)
        return
    
    if data == "tasks_completed":
        handle_completed_tasks(bot, call)
        return
    
    if data == "tasks_progress":
        handle_tasks_progress(bot, call)
        return
    
    if data == "tasks_help":
        handle_tasks_help(bot, call)
        return
    
    # Заглушка для "dummy" кнопок
    if data == "dummy":
        bot.answer_callback_query(call.id)
        return
    
    # РАСПИСАНИЕ (ленивый импорт)
    if data == 'schedule_week':
        bot.answer_callback_query(call.id)
        from schedule_module import handle_schedule_week
        return handle_schedule_week(bot, call.message)
    
    if data == 'schedule_month':
        bot.answer_callback_query(call.id)
        from schedule_module import handle_schedule_month
        return handle_schedule_month(bot, call.message)
    
    if data == 'my_reminders':
        bot.answer_callback_query(call.id, "🔧 Напоминания в разработке!")
        return
    
    # Возврат в главное меню
    if data == 'main_menu':
        user = get_user(user_id)
        display_name = get_user_display_name(user_id)
        
        bot.edit_message_text(
            f"Йоу, {display_name}! 👋\n\nРад тебя видеть! Чем могу помочь?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu_keyboard()
        )
        bot.answer_callback_query(call.id)
        return
    
    # Админские команды
    if data == 'admin_export_db':
        bot.answer_callback_query(call.id)
        return handle_export_db(bot, call.message)
    
    if data == 'admin_without_qr':
        bot.answer_callback_query(call.id)
        return handle_without_qr(bot, call.message)
    
    # TODO: Другие callback'и
    bot.answer_callback_query(call.id, "🔧 В разработке!")

def handle_photo(bot, message):
    """Обработка фото (QR-код или задание)"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # ============ ПРОВЕРКА ОТПРАВКИ ЗАДАНИЯ ============
    if user_id in waiting_for_task_submission:
        if handle_task_submission(bot, message):
            return
    
    # Если пользователь зарегистрирован и отправил фото
    if user and user.get('registration_step', 0) >= 5:
        return handle_qr_photo(bot, message)
    
    # Если регистрация не завершена
    bot.send_message(
        message.chat.id,
        "🤔 Сначала пройди регистрацию!\n\nНапиши /start"
    )

def handle_video(bot, message):
    """Обработка видео (для заданий)"""
    user_id = message.from_user.id
    
    # ============ ПРОВЕРКА ОТПРАВКИ ЗАДАНИЯ ============
    if user_id in waiting_for_task_submission:
        if handle_task_submission(bot, message):
            return
    
    # Если не задание - игнорируем
    bot.send_message(
        message.chat.id,
        "🎥 Видео принято! Если это задание - сначала выбери его в меню 🎯 Задания"
    )

def handle_stat_command(bot, message):
    """Команда /stat (для админа)"""
    return handle_stat(bot, message)

def handle_add_event_command(bot, message):
    """Команда /add_event (для админа)"""
    from schedule_module import handle_add_event_start
    return handle_add_event_start(bot, message)
