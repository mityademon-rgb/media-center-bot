"""
Административные функции
"""
from database import get_statistics, get_recent_users, get_waiting_qr_users
from datetime import datetime
from config import ADMIN_ID

def format_date(date_str):
    """Форматировать дату"""
    if not date_str:
        return "неизвестно"
    
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_str

def get_status_emoji(user):
    """Получить эмодзи статуса пользователя"""
    if user.get('is_registered'):
        return "✅"
    elif user.get('registration_step') == 5:
        return "⏳"
    else:
        return "📝"

def handle_stat(bot, message):
    """Обработка команды /stat"""
    
    # Проверка, что это админ
    if message.chat.id != ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "⛔ Эта команда только для админа!"
        )
        return
    
    # Получаем статистику
    stats = get_statistics()
    recent = get_recent_users(10)
    waiting = get_waiting_qr_users()
    
    # Формируем сообщение
    text = f"""📊 *СТАТИСТИКА БОТА*

👥 *ПОЛЬЗОВАТЕЛИ:*
• Всего: {stats['total']}
• Зарегистрировано: {stats['registered']} ✅
• Ждут QR-код: {stats['waiting_qr']} ⏳
• В процессе регистрации: {stats['in_progress']} 📝

"""
    
    # Последние регистрации
    if recent:
        text += "📋 *ПОСЛЕДНИЕ 10 РЕГИСТРАЦИЙ:*\n\n"
        for i, user in enumerate(recent, 1):
            status = get_status_emoji(user)
            name = f"{user.get('first_name', '?')} {user.get('last_name', '?')}"
            nick = user.get('nickname', '?')
            age = user.get('age', '?')
            date = format_date(user.get('registered_at'))
            
            text += f"{i}. {status} *{name}* (@{nick})\n"
            text += f"   🎂 {age} лет | 🕐 {date}\n\n"
    
    # Кто ждёт QR-код
    if waiting:
        text += f"\n⏳ *ЖДУТ QR-КОД ({len(waiting)}):*\n\n"
        for i, user in enumerate(waiting[:5], 1):
            name = f"{user.get('first_name', '?')} {user.get('last_name', '?')}"
            nick = user.get('nickname', '?')
            date = format_date(user.get('qr_requested_at'))
            
            text += f"{i}. *{name}* (@{nick})\n"
            text += f"   🕐 Запросил: {date}\n\n"
        
        if len(waiting) > 5:
            text += f"_... и ещё {len(waiting) - 5} человек_\n"
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown'
    )

def notify_admin_new_user(bot, user_data, qr_file_id=None):
    """Уведомить админа о новом пользователе"""
    
    name = f"{user_data.get('first_name', '?')} {user_data.get('last_name', '?')}"
    nick = user_data.get('nickname', '?')
    age = user_data.get('age', '?')
    user_id = user_data.get('user_id', '?')
    
    text = f"""✅ *НОВЫЙ УЧАСТНИК НА БОРТУ!*

👤 Имя: {name}
🎮 Ник: {nick}
🎂 Возраст: {age}
🆔 ID: `{user_id}`
"""
    
    if user_data.get('is_registered'):
        text += "\n🎉 *Регистрация завершена!*"
    elif user_data.get('registration_step') == 5:
        text += "\n⏳ *Ожидает QR-код*"
    
    bot.send_message(
        ADMIN_ID,
        text,
        parse_mode='Markdown'
    )
    
    # Если есть QR-код - отправляем его
    if qr_file_id:
        bot.send_photo(
            ADMIN_ID,
            qr_file_id,
            caption=f"📸 QR-код от *{name}* (@{nick})",
            parse_mode='Markdown'
        )
