"""
Обработчики команд и сообщений
"""
import os
from database import get_user, is_registered, get_user_display_name
from registration import start_registration, handle_registration_step, handle_qr_code, handle_nickname_preference
from keyboards import (
    main_menu, profile_menu, calendar_menu, tasks_menu, 
    cheatsheets_menu, links_menu, leaderboard_menu, back_to_main
)
from gamification import get_user_stats, get_leaderboard, get_user_rank, mark_cheatsheet_viewed
from calendar_events import format_schedule_week
from tasks import get_active_task, format_task_message
from texts import CHEATSHEETS
from admin import handle_stat

def handle_start(bot, message):
    """Обработать команду /start"""
    user_id = message.chat.id
    
    # Проверяем зарегистрирован ли пользователь
    if not is_registered(user_id):
        start_registration(bot, message)
        return
    
    # Показываем главное меню
    display_name = get_user_display_name(user_id)
    
    try:
        stats = get_user_stats(user_id)
        level_text = f"📊 Уровень: *{stats['level']} - {stats['level_name']}*\n⭐ Опыт: {stats['xp']} XP\n\n"
    except:
        level_text = ""
    
    bot.send_message(
        user_id,
        f"🎬 Йоу, {display_name}!\n\n"
        f"{level_text}"
        f"Что будем делать?",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

def handle_text(bot, message):
    """Обработать текстовые сообщения"""
    user_id = message.chat.id
    text = message.text
    
    # Проверяем зарегистрирован ли пользователь
    if not is_registered(user_id):
        handle_registration_step(bot, message)
        return
    
    # Обработка кнопок главного меню
    if text == '⭐ Мой профиль':
        show_profile(bot, user_id)
    
    elif text == '📅 Календарь':
        show_calendar(bot, user_id)
    
    elif text == '📸 Задания':
        show_tasks(bot, user_id)
    
    elif text == '📚 Шпаргалки':
        show_cheatsheets(bot, user_id)
    
    elif text == '🏆 Рейтинг':
        show_leaderboard(bot, user_id)
    
    elif text == '🔗 Ссылки':
        show_links(bot, user_id)
    
    else:
        # Если пользователь в процессе регистрации
        user = get_user(user_id)
        if user and user.get('registration_step', 0) < 5:
            handle_registration_step(bot, message)
        else:
            bot.send_message(
                user_id,
                "🤔 Не понял тебя. Используй кнопки меню 👇",
                reply_markup=main_menu()
            )

def handle_photo(bot, message):
    """Обработать фото (QR-код)"""
    user_id = message.chat.id
    
    if not is_registered(user_id):
        bot.send_message(user_id, "⚠️ Сначала пройди регистрацию! Напиши /start")
        return
    
    handle_qr_code(bot, message)

def handle_callback(bot, call):
    """Обработать inline-кнопки"""
    user_id = call.message.chat.id
    
    try:
        # ========== РЕГИСТРАЦИЯ ==========
        
        # Выбор обращения (имя/ник)
        if call.data in ['prefer_name', 'prefer_nickname']:
            handle_nickname_preference(bot, call)
            return
        
        # ========== ГЛАВНОЕ МЕНЮ ==========
        
        # Главное меню
        if call.data == 'main_menu':
            bot.answer_callback_query(call.id)
            display_name = get_user_display_name(user_id)
            
            try:
                stats = get_user_stats(user_id)
                level_text = f"📊 Уровень: *{stats['level']} - {stats['level_name']}*\n⭐ Опыт: {stats['xp']} XP\n\n"
            except:
                level_text = ""
            
            try:
                bot.edit_message_text(
                    f"🎬 Йоу, {display_name}!\n\n"
                    f"{level_text}"
                    f"Что будем делать?",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
            except:
                pass
            
            bot.send_message(
                call.message.chat.id,
                "Используй меню 👇",
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
            
            try:
                bot.edit_message_text(
                    schedule,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=calendar_menu()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                bot.send_message(
                    call.message.chat.id,
                    schedule,
                    parse_mode='Markdown',
                    reply_markup=calendar_menu()
                )
        
        # Календарь - месяц
        elif call.data == 'calendar_month':
            bot.answer_callback_query(call.id, "📆 Расписание на месяц скоро будет!")
        
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
            
            try:
                bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=leaderboard_menu()
                )
            except:
                bot.send_message(
                    call.message.chat.id,
                    text,
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
            
            try:
                bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=leaderboard_menu()
                )
            except:
                bot.send_message(
                    call.message.chat.id,
                    text,
                    parse_mode='Markdown',
                    reply_markup=leaderboard_menu()
                )
        
        # Задания
        elif call.data == 'current_task':
            bot.answer_callback_query(call.id)
            task = get_active_task()
            
            if task:
                text = format_task_message(task)
            else:
                text = "📸 Сейчас нет активных заданий 🤷‍♂️"
            
            try:
                bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=tasks_menu()
                )
            except:
                bot.send_message(
                    call.message.chat.id,
                    text,
                    parse_mode='Markdown',
                    reply_markup=tasks_menu()
                )
        
        elif call.data == 'all_tasks':
            bot.answer_callback_query(call.id, "📋 Список всех заданий скоро будет!")
        
        elif call.data == 'my_tasks':
            bot.answer_callback_query(call.id, "✅ Твои работы скоро будут доступны!")
        
        # Тесты (заглушки)
        elif call.data == 'test_camera':
            bot.answer_callback_query(call.id, "🎥 Тест скоро будет! Следи за обновами 😉")
        
        elif call.data == 'test_journalism':
            bot.answer_callback_query(call.id, "📰 Тест скоро будет! Следи за обновами 😉")
        
        elif call.data == 'test_directing':
            bot.answer_callback_query(call.id, "🎬 Тест скоро будет! Следи за обновами 😉")
        
        else:
            bot.answer_callback_query(call.id)
            
    except Exception as e:
        print(f"❌ Ошибка в handle_callback: {e}")
        import traceback
        print(traceback.format_exc())
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка")

def show_profile(bot, user_id):
    """Показать профиль пользователя"""
    user = get_user(user_id)
    stats = get_user_stats(user_id)
    rank = get_user_rank(user_id)
    
    display_name = get_user_display_name(user_id)
    
    text = f"⭐ *ТВОЙ ПРОФИЛЬ*\n\n"
    text += f"👤 Имя: {user.get('first_name', '—')} {user.get('last_name', '')}\n"
    text += f"🎮 Ник: {user.get('nickname', '—')}\n"
    text += f"🎂 Возраст: {user.get('age', '—')}\n\n"
    text += f"📊 Уровень: *{stats['level']} - {stats['level_name']}*\n"
    text += f"⭐ Опыт: {stats['xp']} XP\n"
    text += f"🏅 Место в рейтинге: {rank if rank else '—'}\n\n"
    text += f"📸 QR-код: {'✅ Загружен' if user.get('qr_code') else '❌ Не загружен'}"
    
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=profile_menu())

def show_calendar(bot, user_id):
    """Показать календарь"""
    schedule = format_schedule_week(user_id)
    bot.send_message(user_id, schedule, parse_mode='Markdown', reply_markup=calendar_menu())

def show_tasks(bot, user_id):
    """Показать задания"""
    task = get_active_task()
    
    if task:
        text = format_task_message(task)
    else:
        text = "📸 *ЗАДАНИЯ*\n\nСейчас нет активных заданий 🤷‍♂️\n\nСледи за обновлениями!"
    
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=tasks_menu())

def show_cheatsheets(bot, user_id):
    """Показать шпаргалки"""
    text = "📚 *ШПАРГАЛКИ*\n\nВыбери тему:"
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=cheatsheets_menu())

def show_leaderboard(bot, user_id):
    """Показать рейтинг"""
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
    
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=leaderboard_menu())

def show_links(bot, user_id):
    """Показать ссылки"""
    text = "🔗 *ПОЛЕЗНЫЕ ССЫЛКИ*\n\nВыбери куда хочешь перейти:"
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=links_menu())

def handle_stat_command(bot, message):
    """Обработать команду /stat (только для админа)"""
    handle_stat(bot, message)
