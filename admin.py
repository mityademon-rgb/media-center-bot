"""
БЛОК 1: АДМИНКА
Статистика и управление пользователями
"""
from database import (
    get_statistics, 
    get_recent_users, 
    get_waiting_qr_users,
    export_database
)
from config import ADMIN_IDS

def is_admin(user_id):
    """Проверка админа"""
    return user_id in ADMIN_IDS

def handle_stat(bot, message):
    """Команда /stat - статистика"""
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Доступ запрещён")
        return
    
    stats = get_statistics()
    recent = get_recent_users(5)
    
    # Формируем сообщение
    text = f"""
📊 **СТАТИСТИКА МЕДИАЦЕНТРА**

👥 Всего пользователей: **{stats['total_users']}**
✅ Зарегистрированы: **{stats['registered_users']}**
🎫 С QR-кодом: **{stats['with_qr']}**
⏳ Без QR: **{stats['without_qr']}**

📈 **Активность:**
• За сегодня: {stats['today_active']} чел.

🆕 **Последние регистрации:**
"""
    
    for i, user in enumerate(recent, 1):
        username = f"@{user.get('telegram_username')}" if user.get('telegram_username') else "без ника"
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        created = user.get('created_at', '')[:10]  # Только дата
        
        text += f"{i}. {name} ({username}) - {created}\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

def handle_export_db(bot, message):
    """Экспорт базы в JSON"""
    if not is_admin(message.from_user.id):
        return
    
    json_data = export_database()
    
    # Отправляем как документ
    from io import BytesIO
    file = BytesIO(json_data.encode('utf-8'))
    file.name = 'users_database.json'
    
    bot.send_document(
        message.chat.id,
        file,
        caption="📥 База данных пользователей"
    )

def handle_without_qr(bot, message):
    """Список пользователей без QR"""
    if not is_admin(message.from_user.id):
        return
    
    waiting = get_waiting_qr_users()
    
    if not waiting:
        bot.send_message(message.chat.id, "✅ Все пользователи загрузили QR!")
        return
    
    text = f"⏳ **Без QR-кода ({len(waiting)} чел.):**\n\n"
    
    for user in waiting:
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        username = f"@{user.get('telegram_username')}" if user.get('telegram_username') else ""
        text += f"• {name} {username}\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')
