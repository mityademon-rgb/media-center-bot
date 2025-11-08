"""
БЛОК 2: РАСПИСАНИЕ ЗАНЯТИЙ
Управление расписанием, просмотр, напоминания
"""
from datetime import datetime, timedelta
from database import get_user, update_user
from keyboards import back_to_menu_keyboard
from telebot import types
import json
import os

# Путь к файлу расписания
SCHEDULE_FILE = os.path.join(os.getenv('DATA_DIR', '/tmp'), 'schedule.json')

# === РАБОТА С ФАЙЛОМ РАСПИСАНИЯ ===

def load_schedule():
    """Загрузить расписание из файла"""
    if not os.path.exists(SCHEDULE_FILE):
        return []
    
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_schedule(schedule):
    """Сохранить расписание в файл"""
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    print(f"💾 Расписание сохранено: {len(schedule)} событий")

def add_event(event_data):
    """Добавить событие в расписание"""
    schedule = load_schedule()
    
    # Генерируем ID
    event_id = max([e.get('id', 0) for e in schedule], default=0) + 1
    event_data['id'] = event_id
    event_data['created_at'] = datetime.now().isoformat()
    
    schedule.append(event_data)
    save_schedule(schedule)
    
    return event_id

def get_events_for_week(start_date=None):
    """Получить события на неделю"""
    if start_date is None:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_date = start_date + timedelta(days=7)
    
    schedule = load_schedule()
    
    week_events = []
    for event in schedule:
        event_date = datetime.fromisoformat(event['date'])
        if start_date <= event_date < end_date:
            week_events.append(event)
    
    # Сортируем по дате
    week_events.sort(key=lambda x: x['date'])
    
    return week_events

def get_events_for_month(year=None, month=None):
    """Получить события на месяц"""
    if year is None:
        now = datetime.now()
        year = now.year
        month = now.month
    
    # Первый день месяца
    start_date = datetime(year, month, 1)
    
    # Последний день месяца
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    schedule = load_schedule()
    
    month_events = []
    for event in schedule:
        event_date = datetime.fromisoformat(event['date'])
        if start_date <= event_date < end_date:
            month_events.append(event)
    
    month_events.sort(key=lambda x: x['date'])
    
    return month_events


# === ОТОБРАЖЕНИЕ РАСПИСАНИЯ ===

def format_event(event):
    """Форматировать событие для отображения"""
    event_date = datetime.fromisoformat(event['date'])
    
    # День недели на русском
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    weekday = weekdays[event_date.weekday()]
    
    date_str = event_date.strftime(f'{weekday}, %d.%m.%Y')
    time_str = event_date.strftime('%H:%M')
    
    result = f"📅 **{date_str}** в **{time_str}**\n"
    result += f"📚 {event['title']}\n"
    
    if event.get('description'):
        result += f"📝 {event['description']}\n"
    
    if event.get('location'):
        result += f"📍 {event['location']}\n"
    
    return result

def handle_schedule_week(bot, message):
    """Показать расписание на неделю"""
    events = get_events_for_week()
    
    if not events:
        bot.send_message(
            message.chat.id,
            "📅 На этой неделе занятий пока нет\n\n"
            "Следи за обновлениями! 👀",
            reply_markup=back_to_menu_keyboard()
        )
        return
    
    text = "📅 **РАСПИСАНИЕ НА НЕДЕЛЮ**\n\n"
    
    for event in events:
        text += format_event(event) + "\n"
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown',
        reply_markup=back_to_menu_keyboard()
    )

def handle_schedule_month(bot, message):
    """Показать расписание на месяц"""
    events = get_events_for_month()
    
    if not events:
        now = datetime.now()
        month_name = now.strftime('%B %Y')
        
        bot.send_message(
            message.chat.id,
            f"📅 В {month_name} занятий пока нет\n\n"
            "Следи за обновлениями! 👀",
            reply_markup=back_to_menu_keyboard()
        )
        return
    
    now = datetime.now()
    month_name = now.strftime('%B %Y')
    
    text = f"📅 **РАСПИСАНИЕ НА {month_name.upper()}**\n\n"
    
    for event in events:
        text += format_event(event) + "\n"
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown',
        reply_markup=back_to_menu_keyboard()
    )


# === АДМИНКА: ДОБАВЛЕНИЕ СОБЫТИЙ ===

def handle_add_event_start(bot, message):
    """Начать добавление события (только для админа)"""
    from admin import is_admin
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "⛔ Доступ запрещён!")
        return
    
    # Сохраняем состояние "добавление события"
    update_user(user_id, {'adding_event': True, 'event_step': 1})
    
    bot.send_message(
        message.chat.id,
        "➕ **ДОБАВЛЕНИЕ ЗАНЯТИЯ**\n\n"
        "📚 Введи название занятия:\n\n"
        "_Например: Основы фотографии_",
        parse_mode='Markdown'
    )

def handle_add_event_step(bot, message):
    """Обработка шагов добавления события"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user or not user.get('adding_event'):
        return False
    
    step = user.get('event_step', 1)
    
    if step == 1:
        # Шаг 1: Название
        update_user(user_id, {
            'event_title': message.text,
            'event_step': 2
        })
        
        bot.send_message(
            message.chat.id,
            "✅ Отлично!\n\n"
            "📝 Теперь введи описание (или напиши `-` чтобы пропустить):\n\n"
            "_Например: Узнаем про композицию, экспозицию и свет_",
            parse_mode='Markdown'
        )
        return True
    
    elif step == 2:
        # Шаг 2: Описание
        description = None if message.text == '-' else message.text
        
        update_user(user_id, {
            'event_description': description,
            'event_step': 3
        })
        
        bot.send_message(
            message.chat.id,
            "✅ Супер!\n\n"
            "📍 Введи место проведения (или `-` чтобы пропустить):\n\n"
            "_Например: Медиацентр, каб. 101_",
            parse_mode='Markdown'
        )
        return True
    
    elif step == 3:
        # Шаг 3: Место
        location = None if message.text == '-' else message.text
        
        update_user(user_id, {
            'event_location': location,
            'event_step': 4
        })
        
        bot.send_message(
            message.chat.id,
            "✅ Окей!\n\n"
            "📅 Введи дату и время в формате:\n\n"
            "`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
            "_Например: 25.12.2024 15:00_",
            parse_mode='Markdown'
        )
        return True
    
    elif step == 4:
        # Шаг 4: Дата и время
        try:
            event_datetime = datetime.strptime(message.text, '%d.%m.%Y %H:%M')
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Неправильный формат!\n\n"
                "Используй: `ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
                "_Например: 25.12.2024 15:00_",
                parse_mode='Markdown'
            )
            return True
        
        # Создаём событие
        event_data = {
            'title': user['event_title'],
            'description': user.get('event_description'),
            'location': user.get('event_location'),
            'date': event_datetime.isoformat()
        }
        
        event_id = add_event(event_data)
        
        # Очищаем состояние
        update_user(user_id, {
            'adding_event': False,
            'event_step': None,
            'event_title': None,
            'event_description': None,
            'event_location': None
        })
        
        # Подтверждение
        confirmation = f"✅ **ЗАНЯТИЕ ДОБАВЛЕНО!**\n\n{format_event(event_data)}"
        confirmation += f"\n📌 ID события: `{event_id}`"
        
        bot.send_message(
            message.chat.id,
            confirmation,
            parse_mode='Markdown'
        )
        
        return True
    

# === АВТОМАТИЧЕСКИЕ НАПОМИНАНИЯ ===

def send_daily_reminders(bot):
    """Отправить напоминания о событиях сегодня (запускается каждый день в 9:00)"""
    from database import get_all_users
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    # События сегодня
    schedule = load_schedule()
    today_events = []
    
    for event in schedule:
        event_date = datetime.fromisoformat(event['date'])
        if today <= event_date < tomorrow:
            today_events.append(event)
    
    if not today_events:
        print("✅ Событий на сегодня нет")
        return
    
    # Формируем сообщение
    text = "🔔 **НАПОМИНАНИЕ О ЗАНЯТИЯХ СЕГОДНЯ!**\n\n"
    
    for event in today_events:
        text += format_event(event) + "\n"
    
    text += "\n📍 Не забудь прийти вовремя! Ждём тебя 🚀"
    
    # Отправляем всем зарегистрированным пользователям
    users = get_all_users()
    sent_count = 0
    
    for user in users:
        # Только зарегистрированным
        if user.get('registration_step', 0) >= 5:
            try:
                bot.send_message(user['user_id'], text, parse_mode='Markdown')
                sent_count += 1
            except Exception as e:
                print(f"⚠️ Не удалось отправить {user['user_id']}: {e}")
    
    print(f"✅ Отправлено {sent_count} напоминаний о {len(today_events)} событиях")

  
