"""
Клавиатуры для бота
"""
from telebot import types

def main_menu():
    """Главное меню"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('⭐ Мой профиль', '📅 Календарь')
    keyboard.row('📸 Задания', '📚 Шпаргалки')
    keyboard.row('🏆 Рейтинг', '🔗 Ссылки')
    return keyboard

def profile_menu():
    """Меню профиля (inline)"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    return keyboard

def calendar_menu():
    """Меню календаря (inline)"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton('📅 На эту неделю', callback_data='calendar_week'),
        types.InlineKeyboardButton('📆 На весь месяц', callback_data='calendar_month')
    )
    keyboard.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    return keyboard

def tasks_menu():
    """Меню заданий (inline)"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton('📸 Текущее задание', callback_data='current_task'),
        types.InlineKeyboardButton('📋 Все задания', callback_data='all_tasks')
    )
    keyboard.add(types.InlineKeyboardButton('✅ Мои работы', callback_data='my_tasks'))
    keyboard.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    return keyboard

def cheatsheets_menu():
    """Меню шпаргалок (inline)"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton('🎥 Камера', callback_data='cheat_camera'),
        types.InlineKeyboardButton('📰 Журналистика', callback_data='cheat_journalism')
    )
    keyboard.row(
        types.InlineKeyboardButton('🎬 Режиссура', callback_data='cheat_directing'),
        types.InlineKeyboardButton('✂️ Монтаж', callback_data='cheat_editing')
    )
    keyboard.row(
        types.InlineKeyboardButton('💡 Советы', callback_data='cheat_tips'),
        types.InlineKeyboardButton('🎨 Композиция', callback_data='cheat_composition')
    )
    keyboard.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    return keyboard

def links_menu():
    """Меню ссылок (inline)"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('🌐 Сайт медиацентра', url='https://dk.mosreg.ru/dk/marfino'))
    keyboard.add(types.InlineKeyboardButton('💬 Чат медиацентра', url='https://t.me/+your_chat_link'))
    keyboard.add(types.InlineKeyboardButton('📱 Instagram', url='https://instagram.com/mediacenter_marfino'))
    keyboard.add(types.InlineKeyboardButton('🎬 YouTube', url='https://youtube.com/@mediacenter_marfino'))
    keyboard.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    return keyboard

def leaderboard_menu():
    """Меню рейтинга (inline)"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton('🏆 Топ-10', callback_data='leaderboard_top10'),
        types.InlineKeyboardButton('📊 Моя позиция', callback_data='my_rank')
    )
    keyboard.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    return keyboard

def back_to_main():
    """Кнопка возврата в главное меню"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    return keyboard

def nickname_preference_keyboard(first_name, nickname):
    """Клавиатура выбора обращения (имя/ник)"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(f'По имени ({first_name})', callback_data='prefer_name'),
        types.InlineKeyboardButton(f'По нику ({nickname})', callback_data='prefer_nickname')
    )
    return keyboard
    
# === ГЛАВНОЕ МЕНЮ ===

def main_menu_keyboard():
    """Главное меню после регистрации"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("📚 Шпаргалки", callback_data="cheatsheets"),
        types.InlineKeyboardButton("📅 Расписание", callback_data="schedule"),
        types.InlineKeyboardButton("🎯 Задания", callback_data="tasks"),
        types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        types.InlineKeyboardButton("📊 Мой прогресс", callback_data="my_stats"),
        types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    ]
    
    markup.add(*buttons)
    return markup

