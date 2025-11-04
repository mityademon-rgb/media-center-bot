"""
Работа с базой данных пользователей
"""
import json
import os
from datetime import datetime

DATABASE_FILE = 'users.json'

def load_users():
    """Загрузить всех пользователей из файла"""
    if not os.path.exists(DATABASE_FILE):
        return {}
    
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    """Сохранить пользователей в файл"""
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def create_user(user_id):
    """Создать нового пользователя"""
    users = load_users()
    
    if str(user_id) in users:
        return users[str(user_id)]
    
    new_user = {
        'user_id': user_id,
        'registration_step': 1,
        'is_registered': False,
        'registered_at': None,
        
        # Геймификация
        'xp': 0,
        'level': 1,
        'attendance': [],  # Список дат посещений
        'attendance_count': 0,
        'events': [],  # Список мероприятий
        'event_count': 0,
        'task_submissions': {},  # Творческие задания
        'task_count': 0,
        'cheatsheets_viewed': [],  # Просмотренные шпаргалки
        'cheatsheet_count': 0,
        'tests_completed': {},  # Пройденные тесты
        'test_count': 0,
        
        'created_at': datetime.now().isoformat()
    }
    
    users[str(user_id)] = new_user
    save_users(users)
    
    return new_user

def get_user(user_id):
    """Получить данные пользователя"""
    users = load_users()
    return users.get(str(user_id))

def update_user(user_id, **kwargs):
    """Обновить данные пользователя"""
    users = load_users()
    
    if str(user_id) not in users:
        return None
    
    users[str(user_id)].update(kwargs)
    save_users(users)
    
    return users[str(user_id)]

def is_registered(user_id):
    """Проверить, зарегистрирован ли пользователь"""
    user = get_user(user_id)
    return user.get('is_registered', False) if user else False

def get_user_display_name(user_id):
    """Получить имя для обращения к пользователю"""
    user = get_user(user_id)
    if not user:
        return "друг"
    
    prefer = user.get('prefer_name', 'name')
    
    if prefer == 'nickname':
        return user.get('nickname', user.get('first_name', 'друг'))
    else:
        return user.get('first_name', 'друг')

def get_statistics():
    """Получить статистику по пользователям"""
    users = load_users()
    
    total = len(users)
    registered = sum(1 for u in users.values() if u.get('is_registered', False))
    waiting_qr = sum(1 for u in users.values() if u.get('registration_step') == 5 and not u.get('qr_code'))
    in_progress = sum(1 for u in users.values() if u.get('registration_step', 999) < 5)
    
    return {
        'total': total,
        'registered': registered,
        'waiting_qr': waiting_qr,
        'in_progress': in_progress
    }

def get_recent_users(limit=10):
    """Получить последних пользователей"""
    users = load_users()
    
    # Сортируем по дате регистрации
    sorted_users = sorted(
        users.values(),
        key=lambda x: x.get('registered_at', ''),
        reverse=True
    )
    
    return sorted_users[:limit]

def get_waiting_qr_users():
    """Получить пользователей, которые ждут QR-код"""
    users = load_users()
    
    waiting = []
    for user_data in users.values():
        if user_data.get('registration_step') == 5 and not user_data.get('qr_code'):
            waiting.append(user_data)
    
    # Сортируем по дате запроса
    waiting.sort(key=lambda x: x.get('qr_requested_at', ''), reverse=True)
    
    return waiting
