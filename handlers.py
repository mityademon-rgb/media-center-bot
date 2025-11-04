"""
Обработчики команд и кнопок
"""
from keyboards import (
    main_menu, profile_menu, calendar_menu, tasks_menu, 
    cheatsheets_menu, links_menu, leaderboard_menu, back_to_main
)
from texts import CHEATSHEETS
from database import is_registered, get_user, get_user_display_name
from registration import start_registration, handle_registration_step, handle_qr_code
from admin import handle_stat
from gamification import get_user_stats, get_leaderboard, get_user_rank, mark_cheatsheet_viewed
from tasks import get_active_task, format_task_message
from calendar_events import format_schedule_week, get_upcoming_events, format_event_details

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
    
    # Получаем статистику
    stats = get_user_stats(user_id)
    
    bot.send_message(
        message.chat.id,
        f"🎬 Йоу, {display_name}! Рад тебя видеть! 🔥\n\n"
        f"📊 Твой уровень: *{stats['level']} - {stats['level_name']}*\n"
        f"⭐ Опыт: {stats['xp']} XP\n\n"
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
    
    # ========== ГЛАВНОЕ МЕНЮ ==========
    
    if text == '⭐ Мой профиль':
        handle_profile(bot, message)
    
    elif text == '📅 Календарь':
        handle_calendar(bot, message)
    
    elif text == '📸 Задания':
        handle_tasks(bot, message)
    
    elif text == '📚 Шпаргалки':
        bot.send_message(
            message.chat.id,
            "📚 *ШПАРГАЛКИ*\n\nВыбирай тему! 👇",
            parse_mode='Markdown',
            reply_markup=cheatsheets_menu()
        )
    
    elif text == '🏆 Рейтинг':
        handle_leaderboard(bot, message)
    
    elif text == '🔗 Ссылки':
        bot.send_message(
            message.chat.id,
            "🔗 *ПОЛЕЗНЫЕ ССЫЛКИ*\n\nКуда хочешь заглянуть? 👇",
            parse_mode='Markdown',
            reply_markup=links_menu()
        )
    
    else:
        bot.send_message(
            message.chat.id,
            "Используй кнопки меню 👇",
            reply_markup=main_menu()
        )

# ========== ОБРАБОТЧИКИ РАЗДЕЛОВ ==========

def handle_profile(bot, message):
    """Показать профиль пользователя"""
    user_id = message.chat.id
    stats = get_user_stats(user_id)
    display_name = get_user_display_name(user_id)
    
    # Прогресс-бар для XP
    progress = stats['progress']
    bar_length = 10
    filled = int(progress / 10)
    bar = '▓' * filled + '░' * (bar_length - filled)
    
    text = f"⭐ *ТВОЙ ПРОФИЛЬ*\n\n"
    text += f"👤 {display_name}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📊 *УРОВЕНЬ:* {stats['level']} - {stats['level_name']}\n"
    text += f"📈 *Опыт:* {stats['xp']} XP\n"
    text += f"{bar} {progress}%\n\n"
    
    if stats['xp_to_next']:
        text += f"До следующего уровня: {stats['xp_to_next']} XP\n\n"
    else:
        text += f"🏆 Максимальный уровень!\n\n"
    
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📚 *СТАТИСТИКА:*\n\n"
    text += f"Занятий посещено: {stats['attendance_count']}\n"
    text += f"Мероприятий: {stats['event_count']}\n"
    text += f"Заданий выполнено: {stats['task_count']}\n"
    text += f"Шпаргалок изучено: {stats['cheatsheet_count']}\n"
    text += f"Тестов пройдено: {stats['test_count']}\n"
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown',
        reply_markup=profile_menu()
    )

def handle_calendar(bot, message):
    """Показать календарь"""
    user_id = message.chat.id
    schedule = format_schedule_week(user_id)
    
    bot.send_message(
        message.chat.id,
        schedule,
        parse_mode='Markdown',
        reply_markup=calendar_menu()
    )

def handle_tasks(bot, message):
    """Показать задания"""
    task = get_active_task()
    
    if task:
        text = format_task_message(task)
    else:
        text = "📸 *ЗАДАНИЯ*\n\nСейчас нет активных заданий 🤷‍♂️\n\nСледи за обновлениями!"
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown',
        reply_markup=tasks_menu()
    )

def handle_leaderboard(bot, message):
    """Показать рейтинг"""
    user_id = message.chat.id
    leaderboard = get_leaderboard(limit=10)
    user_rank = get_user_rank(user_id)
    
    text = "🏆 *РЕЙТИНГ МЕДИАЦЕНТРА*\n\n"
    
    medals = ['🥇', '🥈', '🥉']
    
    for i, user in enumerate(leaderboard, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        name = user.get('first_name', 'Участник')
        xp = user.get('xp', 0)
        
        if user['user_id'] == user_id:
            text += f"*{medal} {name} - {xp} XP* ⬅️ ТЫ\n"
        else:
            text += f"{medal} {name} - {xp} XP\n"
    
    text += f"\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if user_rank:
        if user_rank <= 10:
            text += f"Ты в топ-10! 🔥"
        else:
            text += f"📊 Твоя позиция: {user_rank} место"
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown',
        reply_markup=leaderboard_menu()
    )

# ========== ОБРАБОТКА CALLBACK КНОПОК ==========
def handle_callback(bot, call):
    user_id = call.message.chat.id
    
    # Главное меню
    if call.data == 'main_menu':
        bot.answer_callback_query(call.id)
        display_name = get_user_display_name(user_id)
        stats = get_user_stats(user_id)
        
        bot.edit_message_text(
            f"🎬 Йоу, {display_name}!\n\n"
            f"📊 Уровень: *{stats['level']} - {stats['level_name']}*\n"
            f"⭐ Опыт: {stats['xp']} XP\n\n"
            f"Что будем делать?",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=main_menu()
        )
    
    # Шпаргалки
    elif call.data in CHEATSHEETS:
        bot.answer_callback_query(call.id)
        
        # Отмечаем просмотр и даём XP
        result = mark_cheatsheet_viewed(user_id, call.data)
        
        text = CHEATSHEETS[call.data]
        
        if result and not result.get('already_viewed'):
            text += f"\n\n💰 *+{result['xp_result']['added']} XP!*"
        
        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode='Markdown',
            reply_markup=back_to_main()
        )
    
    # Календарь - неделя
    elif call.data == 'calendar_week':
        bot.answer_callback_query(call.id)
        schedule = format_schedule_week(user_id)
        
        bot.edit_message_text(
            schedule,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=calendar_menu()
        )
    
    # Рейтинг - топ 10
    elif call.data == 'leaderboard_top10':
        bot.answer_callback_query(call.id)
        leaderboard = get_leaderboard(limit=10)
        
        text = "🏆 *ТОП-10 МЕДИАЦЕНТРА*\n\n"
        medals = ['🥇', '🥈', '🥉']
        
        for i, user in enumerate(leaderboard, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = user.get('first_name', 'Участник')
            xp = user.get('xp', 0)
            
            if user['user_id'] == user_id:
                text += f"*{medal} {name} - {xp} XP* ⬅️\n"
            else:
                text += f"{medal} {name} - {xp} XP\n"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=leaderboard_menu()
        )
    
    # Моя позиция в рейтинге
    elif call.data == 'my_rank':
        bot.answer_callback_query(call.id)
        rank = get_user_rank(user_id)
        stats = get_user_stats(user_id)
        
        text = f"📊 *ТВОЯ ПОЗИЦИЯ*\n\n"
        text += f"🏅 Место: {rank if rank else '—'}\n"
        text += f"⭐ Опыт: {stats['xp']} XP\n"
        text += f"📈 Уровень: {stats['level']} - {stats['level_name']}"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=leaderboard_menu()
        )
    
    # Тесты (заглушки)
    elif call.data == 'test_camera':
        bot.answer_callback_query(call.id, "🎥 Тест скоро будет! Следи за обновами 😉")
    
    elif call.data == 'test_journalism':
        bot.answer_callback_query(call.id, "📰 Тест скоро будет! Следи за обновами 😉")
    
    elif call.data == 'test_directing':
        bot.answer_callback_query(call.id, "🎬 Тест скоро будет! Следи за обновами 😉")
    
    else:
        bot.answer_callback_query(call.id)

# ========== ОБРАБОТКА ФОТО (для QR-кода и заданий) ==========
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
        # TODO: Обработка отправки творческого задания
        bot.send_message(
            user_id, 
            "📸 Отправка заданий скоро будет доступна!\n\nИспользуй кнопки меню 👇", 
            reply_markup=main_menu()
        )

# ========== КОМАНДА /STAT (для админа) ==========
def handle_stat_command(bot, message):
    handle_stat(bot, message)
