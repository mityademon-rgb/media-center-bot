"""
Работа с базой данных пользователей
"""
import json
import os
from datetime import datetime, timedelta

DB_FILE = 'users.json'

def load_users():
    """Загрузить пользователей из файла"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Сохранить пользователей в файл"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_user(user_id):
    """Получить данные пользователя"""
    users = load_users()
    return users.get(str(user_id))

def create_user(user_id):
    """Создать нового пользователя"""
    users = load_users()
    users[str(user_id)] = {
        'user_id': user_id,
        'registration_step': 1,
        'first_name': None,
        'last_name': None,
        'nickname': None,
        'age': None,
        'prefer_name': None,  # 'name' или 'nickname'
        'qr_code': None,
        'qr_requested_at': None,
        'qr_reminder_sent': False,
        'registered_at': datetime.now().isoformat(),
        'is_registered': False
    }
    save_users(users)
    return users[str(user_id)]

def update_user(user_id, **kwargs):
    """Обновить данные пользователя"""
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = create_user(user_id)
    
    for key, value in kwargs.items():
        users[str(user_id)][key] = value
    
    save_users(users)
    return users[str(user_id)]

def is_registered(user_id):
    """Проверить, зарегистрирован ли пользователь"""
    user = get_user(user_id)
    return user and user.get('is_registered', False)

def get_users_waiting_qr():
    """Получить пользователей, ожидающих QR-код больше 24 часов"""
    users = load_users()
    waiting = []
    now = datetime.now()
    
    for user_id, user_data in users.items():
        if (user_data.get('qr_requested_at') and 
            not user_data.get('qr_code') and 
            not user_data.get('qr_reminder_sent')):
            
            requested_at = datetime.fromisoformat(user_data['qr_requested_at'])
            if now - requested_at >= timedelta(days=1):
                waiting.append(user_data)
    
    return waiting

def get_user_display_name(user_id):
    """Получить имя для обращения к пользователю"""
    user = get_user(user_id)
    if not user:
        return "друг"
    
    if user.get('prefer_name') == 'nickname' and user.get('nickname'):
        return user['nickname']
    elif user.get('first_name'):
        return user['first_name']
    else:
        return "друг"
