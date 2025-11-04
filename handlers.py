"""
РОУТЕР КОМАНД И СООБЩЕНИЙ
Направляет запросы в соответствующие блоки
"""
from database import get_user, is_registered, update_user
from registration import (
    handle_start_registration,
    handle_registration_step,
    handle_nickname_preference,
    handle_qr_photo
)
from admin import handle_stat, handle_export_db, handle_without_qr, is_admin
from keyboards import main_menu_keyboard

def handle_start(bot, message):
    """Команда /start"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Если пользователя нет или регистрация не завершена
    if not user or not is_registered(user_id):
        return handle_start_registration(bot, message)
    
    # Обновляем активность
    update_user(user_id, {})
    
    # Показываем главное меню
    from database import get_user_display_name
    display_name = get_user_display_name(user_id)
    
    welcome_text = f"""
Йоу, {display_name}! 👋

Рад тебя видеть! Чем могу помочь?
"""
    
    keyboard = main_menu_keyboard()
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=keyboard
    )

def handle_text(bot, message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Если регистрация не завершена - направляем в регистрацию
    if not user or not is_registered(user_id):
        return handle_registration_step(bot, message)
    
    # Обновляем активность
    update_user(user_id, {})
    
    # TODO: Обработка других команд (шпаргалки, задания и т.д.)
    text = message.text.lower()
    
    if text in ['меню', 'главное меню', '/menu']:
        return handle_start(bot, message)
    
    # Если команда не распознана
    bot.send_message(
        message.chat.id,
        "🤔 Не совсем понял... Попробуй выбрать команду из меню!\n\n"
        "Или напиши /start для главного меню"
    )

def handle_callback(bot, call):
    """Обработка нажатий на кнопки"""
    user_id = call.from_user.id
    data = call.data
    
    # Обновляем активность
    update_user(user_id, {})
    
    # Выбор обращения (регистрация шаг 4)
    if data in ['use_name', 'use_nickname']:
        return handle_nickname_preference(bot, call)
    
    # Админские команды
    if data == 'admin_export_db':
        return handle_export_db(bot, call.message)
    
    if data == 'admin_without_qr':
        return handle_without_qr(bot, call.message)
    
    # TODO: Другие callback'и (шпаргалки, задания и т.д.)
    
    bot.answer_callback_query(call.id, "🔧 В разработке!")

def handle_photo(bot, message):
    """Обработка фото (QR-код)"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Если пользователь зарегистрирован и отправил фото
    if user and user.get('registration_step', 0) >= 5:
        return handle_qr_photo(bot, message)
    
    # Если регистрация не завершена
    bot.send_message(
        message.chat.id,
        "🤔 Сначала пройди регистрацию!\n\nНапиши /start"
    )

def handle_stat_command(bot, message):
    """Команда /stat (для админа)"""
    return handle_stat(bot, message)
