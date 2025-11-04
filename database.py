"""
Управление базой данных пользователей (в памяти)
"""
import os
import json
from datetime import datetime

# Глобальная база данных (в памяти)
_users_cache = {}

def load_users():
    """Загрузить пользователей из переменной окружения"""
    global _users_cache
    
    users_data = os.environ.get('USERS_DATABASE', '{}')
    
    try:
        _users_cache = json.loads(users_data)
        print(f"✅ Загружено из переменной: {len(_users_cache)} пользователей")
    except json.JSONDecodeError:
        print("⚠️ Ошибка загрузки базы, создаём пустую")
        _users_cache = {}
    
    return _users_cache

def save_users(users):
    """Сохранить пользователей (в память)"""
    global _users_cache
    _users_cache = users
    print(f"✅ База обновлена: {len(users)} польз.")

def export_database():
    """Экспортировать базу для переменной окружения"""
    users = load_users()
    users_json = json.dumps(users, ensure_ascii=False, indent=2)
    print("\n" + "="*60)
    print("📋 СКОПИРУЙ В ПЕРЕМЕННУЮ USERS_DATABASE:")
    print("="*60)
    print(users_json)
    print("="*60 + "\n")
    return users_json

def get_user(user_id):
    """Получить данные пользователя"""
    users = load_users()
    return users.get(str(user_id))

def create_user(user_id, telegram_data=None):
    """Создать нового пользователя"""
    users = load_users()
    
    user_id_str = str(user_id)
    
    if user_id_str in users:
        print(f"⚠️ Пользователь {user_id} уже существует")
        return users[user_id_str]
    
    # Создаём нового пользователя
    new_user = {
        'user_id': user_id,
        'registration_step': 0,
        'xp': 0,
        'level': 1,
        'tasks_completed': 0,
        'cheatsheets_viewed': [],
        'created_at': datetime.now().isoformat()
    }
    
    # Добавляем данные из Telegram
    if telegram_data:
        new_user.update({
            'telegram_username': telegram_data.get('username'),
            'telegram_first_name': telegram_data.get('first_name'),
            'telegram_last_name': telegram_data.get('last_name')
        })
    
    users[user_id_str] = new_user
    save_users(users)
    
    print(f"✅ Создан пользователь: {user_id}")
    return new_user

def update_user(user_id, updates):
    """Обновить данные пользователя"""
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        print(f"⚠️ Пользователь {user_id} не найден")
        return None
    
    users[user_id_str].update(updates)
    save_users(users)
    
    return users[user_id_str]

def is_registered(user_id):
    """Проверить зарегистрирован ли пользователь"""
    user = get_user(user_id)
    if not user:
        return False
    
    # Проверяем что регистрация завершена (шаг >= 5)
    # Шаг 5 = базовая регистрация завершена, ждём QR
    reg_step = user.get('registration_step', 0)
    return reg_step >= 5

def get_all_users():
    """Получить всех пользователей"""
    return load_users()

def get_user_display_name(user_id):
    """Получить отображаемое имя пользователя"""
    user = get_user(user_id)
    if not user:
        return "друг"
    
    # Проверяем предпочтение: имя или ник
    if user.get('use_nickname'):
        return user.get('nickname', user.get('first_name', 'друг'))
    else:
        return user.get('first_name', 'друг')

def delete_user(user_id):
    """Удалить пользователя"""
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users:
        del users[user_id_str]
        save_users(users)
        print(f"✅ Удалён пользователь: {user_id}")
        return True
    
    return False

# ========== ФУНКЦИИ ДЛЯ АДМИНА ==========

def get_statistics():
    """Получить общую статистику"""
    users = get_all_users()
    
    total_users = len(users)
    registered_users = sum(1 for u in users.values() if u.get('registration_step', 0) >= 5)
    with_qr = sum(1 for u in users.values() if u.get('qr_code'))
    total_xp = sum(u.get('xp', 0) for u in users.values())
    
    return {
        'total_users': total_users,
        'registered_users': registered_users,
        'with_qr': with_qr,
        'without_qr': registered_users - with_qr,
        'total_xp': total_xp,
        'avg_xp': total_xp // total_users if total_users > 0 else 0
    }

def get_recent_users(limit=5):
    """Получить последних зарегистрированных пользователей"""
    users = get_all_users()
    
    # Фильтруем зарегистрированных
    registered = [
        u for u in users.values() 
        if u.get('registration_step', 0) >= 5
    ]
    
    # Сортируем по дате создания (если есть)
    registered.sort(
        key=lambda u: u.get('created_at', ''),
        reverse=True
    )
    
    return registered[:limit]

def get_waiting_qr_users():
    """Получить пользователей без QR-кода"""
    users = get_all_users()
    
    waiting = [
        u for u in users.values()
        if u.get('registration_step', 0) >= 5 and not u.get('qr_code')
    ]
    
    return waiting

# Инициализация при импорте
load_users()
