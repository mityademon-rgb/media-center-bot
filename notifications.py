"""
Система уведомлений о мероприятиях
"""
from datetime import datetime, timedelta
from calendar_events import get_upcoming_events, get_today_events, EVENT_TYPES
from database import load_users

def should_send_reminder(event, hours_before):
    """Проверить, нужно ли отправлять напоминание"""
    event_datetime_str = f"{event['date']} {event['time']}"
    event_datetime = datetime.strptime(event_datetime_str, '%Y-%m-%d %H:%M')
    now = datetime.now()
    
    time_diff = event_datetime - now
    hours_diff = time_diff.total_seconds() / 3600
    
    # Если осталось примерно N часов (с погрешностью ±0.5 часа)
    return hours_before - 0.5 <= hours_diff <= hours_before + 0.5

def get_users_for_notification(event):
    """Получить список пользователей для уведомления"""
    users = load_users()
    
    # Если есть список записавшихся - уведомляем их
    participants = event.get('participants', [])
    if participants:
        return [users[uid] for uid in participants if uid in users]
    
    # Иначе уведомляем всех зарегистрированных
    return [u for u in users.values() if u.get('is_registered', False)]

def format_event_reminder(event, hours_before):
    """Форматировать напоминание о событии"""
    event_type = EVENT_TYPES.get(event['type'], {})
    emoji = event_type.get('emoji', '📌')
    
    if hours_before == 24:
        time_text = "ЗАВТРА"
    elif hours_before == 2:
        time_text = "ЧЕРЕЗ 2 ЧАСА"
    elif hours_before == 0:
        time_text = "ПРЯМО СЕЙЧАС"
    else:
        time_text = f"ЧЕРЕЗ {hours_before} ЧАСОВ"
    
    text = f"⏰ *НАПОМИНАНИЕ!*\n\n"
    text += f"{time_text} начинается:\n\n"
    text += f"{emoji} *{event['title']}*\n\n"
    text += f"📅 {event['date']}\n"
    text += f"🕐 {event['time']}\n"
    text += f"📍 {event['location']}\n\n"
    
    if event.get('notes'):
        text += f"ℹ️ *Не забудь:*\n{event['notes']}\n\n"
    
    text += f"💰 За участие: +{event_type.get('xp', 50)} XP\n\n"
    text += "Увидимся! 🔥"
    
    return text

def format_today_schedule():
    """Форматировать расписание на сегодня"""
    events = get_today_events()
    
    if not events:
        return None
    
    text = "🌅 *ДОБРОЕ УТРО!*\n\n"
    text += "📅 *СЕГОДНЯ У НАС:*\n\n"
    
    for event in events:
        event_type = EVENT_TYPES.get(event['type'], {})
        emoji = event_type.get('emoji', '📌')
        
        text += f"{emoji} *{event['title']}*\n"
        text += f"🕐 {event['time']}\n"
        text += f"📍 {event['location']}\n"
        text += f"💰 +{event_type.get('xp', 50)} XP\n\n"
    
    text += "Увидимся! Будет огонь! 🔥"
    
    return text

def format_week_preview():
    """Форматировать анонс на неделю"""
    events = get_upcoming_events(days=7)
    
    if not events:
        return None
    
    text = "🎬 *ПЛАНЫ НА НЕДЕЛЮ!*\n\n"
    text += "Держи расписание, чтобы ничего не пропустить:\n\n"
    
    current_date = None
    for event in events:
        event_date = datetime.strptime(event['date'], '%Y-%m-%d')
        date_str = event_date.strftime('%d.%m')
        day_name = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'][event_date.weekday()]
        
        if event['date'] != current_date:
            if current_date is not None:
                text += "\n"
            text += f"📆 *{day_name}, {date_str}*\n"
            current_date = event['date']
        
        event_type = EVENT_TYPES.get(event['type'], {})
        emoji = event_type.get('emoji', '📌')
        
        text += f"{emoji} {event['time']} - {event['title']}\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "Будет жарко! Готовься! 🔥"
    
    return text

def send_event_reminders(bot):
    """Отправить напоминания о событиях (вызывается по расписанию)"""
    events = get_upcoming_events(days=2)
    sent_count = 0
    
    for event in events:
        # Напоминание за 24 часа
        if should_send_reminder(event, 24):
            users = get_users_for_notification(event)
            message = format_event_reminder(event, 24)
            
            for user in users:
                try:
                    bot.send_message(user['user_id'], message, parse_mode='Markdown')
                    sent_count += 1
                except Exception as e:
                    print(f"Ошибка отправки напоминания пользователю {user['user_id']}: {e}")
        
        # Напоминание за 2 часа
        elif should_send_reminder(event, 2):
            users = get_users_for_notification(event)
            message = format_event_reminder(event, 2)
            
            for user in users:
                try:
                    bot.send_message(user['user_id'], message, parse_mode='Markdown')
                    sent_count += 1
                except Exception as e:
                    print(f"Ошибка отправки напоминания пользователю {user['user_id']}: {e}")
    
    return sent_count

def send_morning_schedule(bot):
    """Отправить утреннее расписание (вызывается в 9:00)"""
    message = format_today_schedule()
    
    if not message:
        return 0
    
    users = load_users()
    registered_users = [u for u in users.values() if u.get('is_registered', False)]
    
    sent_count = 0
    for user in registered_users:
        try:
            bot.send_message(user['user_id'], message, parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            print(f"Ошибка отправки утреннего сообщения пользователю {user['user_id']}: {e}")
    
    return sent_count

def send_week_preview(bot):
    """Отправить анонс недели (вызывается в воскресенье вечером)"""
    message = format_week_preview()
    
    if not message:
        return 0
    
    users = load_users()
    registered_users = [u for u in users.values() if u.get('is_registered', False)]
    
    sent_count = 0
    for user in registered_users:
        try:
            bot.send_message(user['user_id'], message, parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            print(f"Ошибка отправки анонса недели пользователю {user['user_id']}: {e}")
    
    return sent_count
