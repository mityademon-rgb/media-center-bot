"""
Календарь мероприятий медиацентра
"""
from datetime import datetime, timedelta
from config import CLASS_DAYS, CLASS_TIME

# ========== ТИПЫ СОБЫТИЙ ==========

EVENT_TYPES = {
    'class': {
        'emoji': '📚',
        'name': 'Занятие',
        'xp': 50
    },
    'event': {
        'emoji': '🎬',
        'name': 'Мероприятие',
        'xp': 100
    },
    'shooting': {
        'emoji': '🎥',
        'name': 'Съёмка',
        'xp': 100
    },
    'masterclass': {
        'emoji': '🎓',
        'name': 'Мастер-класс',
        'xp': 75
    }
}

# ========== СПИСОК МЕРОПРИЯТИЙ ==========
# Реальное расписание медиацентра на ноябрь 2024

EVENTS = {
    'nov_6': {
        'id': 'nov_6',
        'type': 'class',
        'title': 'Обсуждение сценария "Последняя мелодия"',
        'description': 'Разбираем сценарий нашего нового фильма, распределяем роли',
        'location': 'Медиацентр Марфино',
        'date': '2024-11-06',
        'time': '18:00',
        'duration': '2 часа',
        'participants_needed': 30,
        'participants': [],
        'notes': '📝 Принеси блокнот для записей!',
        'active': True
    },
    
    'nov_8_kapustnik': {
        'id': 'nov_8_kapustnik',
        'type': 'shooting',
        'title': 'Съёмка "Капустник"',
        'description': 'Снимаем капустник! Нужны операторы и монтажёры',
        'location': 'ДК Марфино',
        'date': '2024-11-08',
        'time': '11:00',
        'duration': '4 часа',
        'participants_needed': 10,
        'participants': [],
        'notes': '📝 Принеси блокнот и ручку',
        'active': True
    },
    
    'nov_8_scenario': {
        'id': 'nov_8_scenario',
        'type': 'class',
        'title': 'Обсуждение сценария "Последняя мелодия"',
        'description': 'Продолжаем работу над сценарием, обсуждаем детали',
        'location': 'Медиацентр Марфино',
        'date': '2024-11-08',
        'time': '15:00',
        'duration': '2 часа',
        'participants_needed': 30,
        'participants': [],
        'notes': '⏰ После съёмки капустника',
        'active': True
    },
    
    'nov_12_interview': {
        'id': 'nov_12_interview',
        'type': 'class',
        'title': 'Занятие: "Всё про интервью"',
        'description': 'Учимся брать интервью: какие вопросы задавать, как себя вести, работа с камерой',
        'location': 'Медиацентр Марфино',
        'date': '2024-11-12',
        'time': '18:00',
        'duration': '2 часа',
        'participants_needed': 30,
        'participants': [],
        'notes': '💡 Подготовь 3 вопроса для тренировки интервью',
        'active': True
    },
    
    'nov_12_scenario': {
        'id': 'nov_12_scenario',
        'type': 'class',
        'title': 'Обсуждение сценария "Последняя мелодия"',
        'description': 'Финальное обсуждение сценария перед началом съёмок',
        'location': 'Медиацентр Марфино',
        'date': '2024-11-12',
        'time': '20:00',
        'duration': '1 час',
        'participants_needed': 30,
        'participants': [],
        'notes': '🎬 После занятия про интервью. Готовимся к съёмкам!',
        'active': True
    },
    
    'nov_15_ai': {
        'id': 'nov_15_ai',
        'type': 'masterclass',
        'title': 'Мастер-класс: "Нейросети"',
        'description': 'Как использовать нейросети в создании контента: картинки, видео, тексты',
        'location': 'Медиацентр Марфино',
        'date': '2024-11-15',
        'time': '16:00',
        'duration': '2 часа',
        'participants_needed': 25,
        'participants': [],
        'notes': '🤖 Время может измениться - следи за уведомлениями!\n💻 Можешь принести ноутбук',
        'active': True
    },
    
    'nov_19_prep': {
        'id': 'nov_19_prep',
        'type': 'class',
        'title': 'Подготовка к съёмке "Последняя мелодия"',
        'description': 'Финальная подготовка перед первым съёмочным днём: распределение ролей, план съёмок',
        'location': 'Медиацентр Марфино',
        'date': '2024-11-19',
        'time': '18:00',
        'duration': '2 часа',
        'participants_needed': 30,
        'participants': [],
        'notes': '🎬 Важно! Без этой встречи на съёмку не пускаем 😉',
        'active': True
    },
    
    'nov_22_shooting': {
        'id': 'nov_22_shooting',
        'type': 'shooting',
        'title': 'ПЕРВЫЙ СЪЁМОЧНЫЙ ДЕНЬ "Последняя мелодия"',
        'description': 'Начинаем снимать наш фильм! Нужны все: актёры, операторы, свет, звук',
        'location': 'Локация уточняется',
        'date': '2024-11-22',
        'time': '10:00',
        'duration': '6-8 часов',
        'participants_needed': 25,
        'participants': [],
        'notes': '🔥 ВАЖНО:\n🍕 Возьми еду и воду\n👕 Сменная одежда (если нужно по роли)\n⏰ Приходи вовремя!',
        'active': True
    },
    
    'nov_28_supermom': {
        'id': 'nov_28_supermom',
        'type': 'shooting',
        'title': 'Съёмка "Супер МАМА"',
        'description': 'Снимаем проект про мам! Нужны операторы и монтажёры',
        'location': 'Локация уточняется',
        'date': '2024-11-28',
        'time': '18:00',
        'duration': '3 часа',
        'participants_needed': 10,
        'participants': [],
        'notes': '📝 Принеси блокнот для заметок',
        'active': True
    }
}

    
    'event_2': {
        'id': 'event_2',
        'type': 'masterclass',
        'title': 'Мастер-класс: Интервью с экспертом',
        'description': 'Учимся брать интервью у профессионалов',
        'location': 'Медиацентр Марфино, Студия 2',
        'date': '2024-11-15',
        'time': '16:00',
        'duration': '2 часа',
        'participants_needed': 15,
        'participants': [],
        'teacher': 'Анна Петрова',
        'guest': 'Иван Сидоров (журналист)',
        'notes': 'Подготовь 3 вопроса заранее',
        'active': True
    }
}

# ========== ФУНКЦИИ ==========

def get_next_classes(weeks=2):
    """Получить расписание занятий на N недель вперёд"""
    classes = []
    today = datetime.now()
    
    for i in range(weeks * 7):
        check_date = today + timedelta(days=i)
        
        if check_date.weekday() in CLASS_DAYS:
            classes.append({
                'type': 'class',
                'date': check_date.strftime('%Y-%m-%d'),
                'time': CLASS_TIME,
                'day_name': ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'][check_date.weekday()],
                'date_formatted': check_date.strftime('%d.%m')
            })
    
    return classes

def get_upcoming_events(days=14):
    """Получить предстоящие мероприятия на N дней"""
    upcoming = []
    today = datetime.now()
    
    for event in EVENTS.values():
        if not event.get('active'):
            continue
        
        event_date = datetime.strptime(event['date'], '%Y-%m-%d')
        days_diff = (event_date - today).days
        
        if 0 <= days_diff <= days:
            upcoming.append(event)
    
    # Сортируем по дате
    upcoming.sort(key=lambda x: x['date'])
    
    return upcoming

def get_event_by_id(event_id):
    """Получить мероприятие по ID"""
    return EVENTS.get(event_id)

def register_for_event(user_id, event_id):
    """Записать пользователя на мероприятие"""
    event = EVENTS.get(event_id)
    if not event:
        return {'success': False, 'reason': 'event_not_found'}
    
    participants = event.get('participants', [])
    
    # Проверяем, не записан ли уже
    if user_id in participants:
        return {'success': False, 'reason': 'already_registered'}
    
    # Проверяем лимит участников
    max_participants = event.get('participants_needed', 999)
    if len(participants) >= max_participants:
        return {'success': False, 'reason': 'event_full'}
    
    # Записываем
    participants.append(user_id)
    event['participants'] = participants
    
    return {
        'success': True,
        'event': event,
        'participants_count': len(participants)
    }

def unregister_from_event(user_id, event_id):
    """Отменить запись на мероприятие"""
    event = EVENTS.get(event_id)
    if not event:
        return {'success': False, 'reason': 'event_not_found'}
    
    participants = event.get('participants', [])
    
    if user_id not in participants:
        return {'success': False, 'reason': 'not_registered'}
    
    participants.remove(user_id)
    event['participants'] = participants
    
    return {'success': True}

def format_schedule_week(user_id=None):
    """Форматировать расписание на неделю"""
    classes = get_next_classes(weeks=1)
    events = get_upcoming_events(days=7)
    
    text = "📅 *РАСПИСАНИЕ НА НЕДЕЛЮ*\n\n"
    
    # Занятия
    text += "📚 *ЗАНЯТИЯ:*\n"
    for cls in classes:
        text += f"{cls['day_name']}, {cls['date_formatted']} в {cls['time']}\n"
    
    text += f"\n💰 За посещение: +50 XP каждое\n"
    
    # Мероприятия
    if events:
        text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for event in events:
            event_type = EVENT_TYPES.get(event['type'], {})
            emoji = event_type.get('emoji', '📌')
            
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            date_str = event_date.strftime('%d.%m')
            day_name = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'][event_date.weekday()]
            
            text += f"{emoji} *{event['title']}*\n"
            text += f"{day_name}, {date_str} в {event['time']}\n"
            text += f"📍 {event['location']}\n"
            
            participants = event.get('participants', [])
            max_p = event.get('participants_needed', 0)
            
            if user_id in participants:
                text += f"✅ Ты записан!\n"
            else:
                text += f"👥 Мест: {len(participants)}/{max_p}\n"
            
            text += f"💰 +{event_type.get('xp', 100)} XP\n\n"
    
    return text

def format_event_details(event_id, user_id=None):
    """Детальная информация о мероприятии"""
    event = get_event_by_id(event_id)
    if not event:
        return "Мероприятие не найдено"
    
    event_type = EVENT_TYPES.get(event['type'], {})
    emoji = event_type.get('emoji', '📌')
    type_name = event_type.get('name', 'Событие')
    
    event_date = datetime.strptime(event['date'], '%Y-%m-%d')
    date_str = event_date.strftime('%d.%m.%Y')
    day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][event_date.weekday()]
    
    text = f"{emoji} *{event['title']}*\n\n"
    text += f"📋 *Тип:* {type_name}\n"
    text += f"📅 *Дата:* {day_name}, {date_str}\n"
    text += f"🕐 *Время:* {event['time']}\n"
    text += f"⏱️ *Длительность:* {event['duration']}\n"
    text += f"📍 *Место:* {event['location']}\n\n"
    
    if event.get('teacher'):
        text += f"👨‍🏫 *Ведущий:* {event['teacher']}\n"
    
    if event.get('guest'):
        text += f"🎤 *Гость:* {event['guest']}\n"
    
    text += f"\n📝 *Описание:*\n{event['description']}\n\n"
    
    participants = event.get('participants', [])
    max_p = event.get('participants_needed', 0)
    text += f"👥 *Участники:* {len(participants)}/{max_p}\n\n"
    
    if event.get('notes'):
        text += f"ℹ️ *Важно:*\n{event['notes']}\n\n"
    
    text += f"💰 *Награда:* +{event_type.get('xp', 100)} XP\n\n"
    
    if user_id in participants:
        text += "✅ *Ты записан на это мероприятие!*"
    else:
        if len(participants) >= max_p:
            text += "❌ *Мест нет (набор завершён)*"
        else:
            text += "Запишись прямо сейчас! 👇"
    
    return text
