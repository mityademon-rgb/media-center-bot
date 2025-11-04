"""
БЛОК 1: УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ
Хранение: JSON файл в постоянном Volume
"""
import os
import json
from datetime import datetime

# Путь к файлу базы (в постоянном хранилище Railway)
DB_FILE = '/data/users.json'

# Резервная копия в /tmp если /data недоступна
BACKUP_DB = '/tmp/users.json'

# Глобальный кэш
_users_cache = {}

def _get_db_path():
    """Определить путь к файлу БД"""
    if os.path.exists('/data') and os.access('/data', os.W_OK):
        return DB_FILE
    else:
        print("⚠️ /data недоступна, используем /tmp")
        return BACKUP_DB

def load_users():
    """Загрузить пользователей из файла"""
    global _users_cache
    
    db_path = _get_db_path()
    
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                _users_cache = json.load(f)
            print(f"✅ Загружено: {len(_users_cache)} пользователей")
            return _users_cache
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
    
    # Если файла нет - создаём пустую базу
    _users_cache = {}
    save_users(_users_cache)
    print("✅ Создана новая база")
    return _users_cache

def save_users(users):
    """Сохранить пользователей в файл"""
    global _users_cache
    _users_cache = users
    
    db_path = _get_db_path()
    
    try:
        # Создаём директорию если нет
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        print(f"💾 База сохранена: {len(users)} польз.")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def get_user(user_id):
    """Получить данные пользователя"""
    users = load_users()
    return users.get(str(user_id))

def create_user(user_id, telegram_data=None):
    """Создать нового пользователя"""
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users:
        return users[user_id_str]
    
    new_user = {
        'user_id': user_id,
        'registration_step': 0,
        'xp': 0,
        'level': 1,
        'tasks_completed': 0,
        'cheatsheets_viewed': [],
        'created_at': datetime.now().isoformat(),
        'last_active': datetime.now().isoformat()
    }
    
    if telegram_data:
        new_user.update({
            'telegram_username': telegram_data.get('username'),
            'telegram_first_name': telegram_data.get('first_name'),
            'telegram_last_name': telegram_data.get('last_name')
        })
    
    users[user_id_str] = new_user
    save_users(users)
    
    print(f"✅ Создан: {user_id}")
    return new_user

def update_user(user_id, updates):
    """Обновить данные пользователя"""
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        return None
    
    users[user_id_str].update(updates)
    users[user_id_str]['last_active'] = datetime.now().isoformat()
    save_users(users)
    
    return users[user_id_str]

def is_registered(user_id):
    """Проверить завершена ли регистрация"""
    user = get_user(user_id)
    if not user:
        return False
    return user.get('registration_step', 0) >= 5

def get_all_users():
    """Получить всех пользователей"""
    return load_users()

def get_user_display_name(user_id):
    """Получить отображаемое имя"""
    user = get_user(user_id)
    if not user:
        return "друг"
    
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
        return True
    return False

# === ФУНКЦИИ ДЛЯ АДМИНА ===

def get_statistics():
    """Статистика для админа"""
    users = get_all_users()
    
    total = len(users)
    registered = sum(1 for u in users.values() if u.get('registration_step', 0) >= 5)
    with_qr = sum(1 for u in users.values() if u.get('qr_code'))
    
    # Активность за сегодня
    today = datetime.now().date().isoformat()
    today_active = sum(
        1 for u in users.values() 
        if u.get('last_active', '').startswith(today)
    )
    
    return {
        'total_users': total,
        'registered_users': registered,
        'with_qr': with_qr,
        'without_qr': registered - with_qr,
        'today_active': today_active
    }

def get_recent_users(limit=5):
    """Последние зарегистрированные"""
    users = get_all_users()
    
    registered = [
        u for u in users.values() 
        if u.get('registration_step', 0) >= 5
    ]
    
    registered.sort(
        key=lambda u: u.get('created_at', ''),
        reverse=True
    )
    
    return registered[:limit]

def get_waiting_qr_users():
    """Пользователи без QR-кода"""
    users = get_all_users()
    
    return [
        u for u in users.values()
        if u.get('registration_step', 0) >= 5 and not u.get('qr_code')
    ]

def export_database():
    """Экспорт базы в JSON"""
    users = get_all_users()
    return json.dumps(users, ensure_ascii=False, indent=2)

# Инициализация
load_users()
