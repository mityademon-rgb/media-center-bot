"""
Работа с базой данных пользователей (через переменные окружения)
"""
import json
import os
from datetime import datetime

# Кэш базы данных в памяти
_users_cache = None

def load_users():
    """Загрузить всех пользователей"""
    global _users_cache
    
    # Если есть в кэше - возвращаем
    if _users_cache is not None:
        return _users_cache
    
    # Пытаемся загрузить из переменной окружения
    users_json = os.environ.get('USERS_DATABASE', '{}')
    
    try:
        _users_cache = json.loads(users_json)
        print(f"✅ Загружено из переменной: {len(_users_cache)} пользователей")
    except:
        _users_cache = {}
        print("⚠️ База данных пуста, создаём новую")
    
    return _users_cache

def save_users(users):
    """Сохранить пользователей (в память)"""
    global _users_cache
    _users_cache = users
    print(f"✅ База в памяти обновлена: {len(users)} пользователей")
    
    # Выводим JSON для копирования в переменную окружения
    users_json = json.dumps(users, ensure_ascii=False)
    print(f"\n📋 СКОПИРУЙ ЭТО В ПЕРЕМЕННУЮ USERS_DATABASE:")
    print(f"{users_json[:200]}..." if len(users_json) > 200 else users_json)
    print()

def get_user(user_id):
    """Получить данные пользователя"""
    users = load_users()
    return users.get(str(user_id))

def save_user(user_id, user_data):
    """Сохранить данные пользователя"""
    users = load_users()
    users[str(user_id)] = user_data
    save_users(users)

def update_user(user_id, updates):
    """Обновить данные пользователя"""
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        return False
    
    users[user_id_str].update(updates)
    save_users(users)
    return True

def get_all_users():
    """Получить всех пользователей"""
    return load_users()

def is_registered(user_id):
    """Проверить зарегистрирован ли пользователь"""
    user = get_user(user_id)
    if not user:
        return False
    
    reg_step = user.get('registration_step', 0)
    return reg_step >= 6

def get_user_display_name(user_id):
    """Получить отображаемое имя пользователя"""
    user = get_user(user_id)
    if not user:
        return "Участник"
    
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    
    if first_name and last_name:
        return f"{first_name} {last_name}"
    elif first_name:
        return first_name
    else:
        return "Участник"

def create_user(user_id, telegram_data):
    """Создать нового пользователя"""
    user_data = {
        'user_id': user_id,
        'telegram_username': telegram_data.get('username'),
        'registration_date': datetime.now().isoformat(),
        'registration_step': 0,
        'xp': 0,
        'level': 1,
        'attendance': [],
        'achievements': [],
        'tasks_completed': [],
        'cheatsheets_viewed': [],
        'tests_passed': []
    }
    
    save_user(user_id, user_data)
    return user_data
