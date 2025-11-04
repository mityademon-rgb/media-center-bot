"""
БЛОК АДМИНКИ
Только для пользователей из ADMIN_IDS
"""
from database import get_all_users, get_waiting_qr_users
import json
from datetime import datetime

# === СПИСОК АДМИНОВ (ДОБАВЬ СВОЙ USER_ID!) ===
ADMIN_IDS = [397724997]  # ← ТВОЙ TELEGRAM USER_ID!

def is_admin(user_id):
    """Проверка: является ли пользователь админом"""
    return user_id in ADMIN_IDS

def handle_stat(bot, message):
    """Команда /stat - статистика бота"""
    user_id = message.from_user.id
    
    print(f"🔍 /stat запрос от user_id={user_id}")
    print(f"🔍 Список админов: {ADMIN_IDS}")
    print(f"🔍 Является админом: {is_admin(user_id)}")
    
    if not is_admin(user_id):
        bot.send_message(
            message.chat.id,
            "⛔ Эта команда только для администраторов!"
        )
        return
    
    # Собираем статистику
    all_users = get_all_users()
    waiting_qr = get_waiting_qr_users()
    
    registered_users = [u for u in all_users if u.get('registration_step', 0) >= 5]
    with_qr = [u for u in all_users if u.get('qr_code')]
    
    stat_text = f"""
📊 **СТАТИСТИКА МЕДИАЦЕНТРА**

👥 **Пользователи:**
• Всего: {len(all_users)}
• Зарегистрированы: {len(registered_users)}
• С QR-кодом: {len(with_qr)}
• Ждут QR: {len(waiting_qr)}

📈 **Активность:**
• Активных сегодня: {len([u for u in all_users if u.get('last_activity')])}

⏰ Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
    
    bot.send_message(message.chat.id, stat_text, parse_mode='Markdown')

def handle_export_db(bot, message):
    """Экспорт базы данных в JSON"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "⛔ Доступ запрещён!")
        return
    
    all_users = get_all_users()
    
    # Конвертируем в JSON
    db_json = json.dumps(all_users, ensure_ascii=False, indent=2)
    
    # Отправляем как файл
    filename = f"database_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    
    bot.send_document(
        message.chat.id,
        document=db_json.encode('utf-8'),
        visible_file_name=filename,
        caption=f"📥 Экспорт базы данных\n\n👥 Пользователей: {len(all_users)}"
    )

def handle_without_qr(bot, message):
    """Список пользователей без QR-кода"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "⛔ Доступ запрещён!")
        return
    
    waiting = get_waiting_qr_users()
    
    if not waiting:
        bot.send_message(message.chat.id, "✅ Все пользователи загрузили QR-коды!")
        return
    
    users_list = []
    for user in waiting:
        name = f"{user.get('first_name', '?')} {user.get('last_name', '?')}"
        nickname = user.get('nickname', '—')
        username = user.get('telegram_username', '—')
        
        users_list.append(
            f"• {name} (@{username})\n"
            f"  Ник: {nickname}\n"
            f"  ID: `{user['user_id']}`"
        )
    
    result_text = f"⏳ **Ждут загрузки QR-кода ({len(waiting)}):**\n\n" + "\n\n".join(users_list)
    
    bot.send_message(message.chat.id, result_text, parse_mode='Markdown')
