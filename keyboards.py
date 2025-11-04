"""
Клавиатуры бота
"""
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import LINKS

def main_menu():
    """Главное меню"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton('⭐ Мой профиль'),
        KeyboardButton('📅 Календарь')
    )
    markup.add(
        KeyboardButton('📸 Задания'),
        KeyboardButton('📚 Шпаргалки')
    )
    markup.add(
        KeyboardButton('🏆 Рейтинг'),
        KeyboardButton('🔗 Ссылки')
    )
    return markup

def profile_menu():
    """Меню профиля"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('🏆 Мои ачивки', callback_data='my_achievements')
    )
    markup.add(
        InlineKeyboardButton('📊 Статистика', callback_data='my_stats')
    )
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup

def calendar_menu():
    """Меню календаря"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('📅 На эту неделю', callback_data='calendar_week')
    )
    markup.add(
        InlineKeyboardButton('📆 На весь месяц', callback_data='calendar_month')
    )
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup

def event_details_menu(event_id, is_registered=False):
    """Меню конкретного мероприятия"""
    markup = InlineKeyboardMarkup()
    
    if is_registered:
        markup.add(
            InlineKeyboardButton('❌ Отменить запись', callback_data=f'unregister_{event_id}')
        )
    else:
        markup.add(
            InlineKeyboardButton('✅ Записаться', callback_data=f'register_{event_id}')
        )
    
    markup.add(
        InlineKeyboardButton('◀️ Назад к календарю', callback_data='calendar_week')
    )
    return markup

def tasks_menu():
    """Меню заданий"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('📸 Текущее задание', callback_data='current_task')
    )
    markup.add(
        InlineKeyboardButton('📋 Все задания', callback_data='all_tasks')
    )
    markup.add(
        InlineKeyboardButton('✅ Мои работы', callback_data='my_tasks')
    )
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup

def task_action_menu(task_id):
    """Меню действий с заданием"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('📤 Отправить работу', callback_data=f'submit_task_{task_id}')
    )
    markup.add(
        InlineKeyboardButton('💡 Подсказки', callback_data=f'task_tips_{task_id}')
    )
    markup.add(
        InlineKeyboardButton('◀️ Назад', callback_data='current_task')
    )
    return markup

def cheatsheets_menu():
    """Меню шпаргалок"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('🎥 Как снимать интервью', callback_data='cheat_interview'),
        InlineKeyboardButton('🏠 Съёмка в помещении', callback_data='cheat_indoor')
    )
    markup.add(
        InlineKeyboardButton('🌳 Съёмка на улице', callback_data='cheat_outdoor'),
        InlineKeyboardButton('🎬 Основы монтажа', callback_data='cheat_editing')
    )
    markup.add(
        InlineKeyboardButton('💡 Работа со светом', callback_data='cheat_light'),
        InlineKeyboardButton('🎤 Работа со звуком', callback_data='cheat_sound')
    )
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup

def links_menu():
    """Меню полезных ссылок"""
    markup = InlineKeyboardMarkup()
    
    for name, url in LINKS.items():
        markup.add(InlineKeyboardButton(name, url=url))
    
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup

def leaderboard_menu():
    """Меню рейтинга"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('🏆 Топ-10', callback_data='leaderboard_top10')
    )
    markup.add(
        InlineKeyboardButton('📊 Моя позиция', callback_data='my_rank')
    )
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup

def tests_menu():
    """Меню тестов"""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🎥 Тест: Операторское мастерство', callback_data='test_camera'),
        InlineKeyboardButton('📰 Тест: Основы журналистики', callback_data='test_journalism'),
        InlineKeyboardButton('🎬 Тест: Режиссура', callback_data='test_directing')
    )
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup

def back_to_main():
    """Кнопка возврата в главное меню"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu')
    )
    return markup
