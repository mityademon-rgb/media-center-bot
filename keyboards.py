"""
Все кнопки и меню
"""
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import LINKS

# ========== ГЛАВНОЕ МЕНЮ ==========
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('📚 Шпаргалки'),
        KeyboardButton('🔗 Полезные ссылки')
    )
    markup.add(KeyboardButton('🎯 Тесты'))
    return markup

# ========== МЕНЮ ШПАРГАЛОК ==========
def cheatsheets_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🎬 Как снимать концерт', callback_data='sheet_concert'),
        InlineKeyboardButton('🎤 Как снимать интервью', callback_data='sheet_interview'),
        InlineKeyboardButton('🌆 Как снимать на улице', callback_data='sheet_street'),
        InlineKeyboardButton('🏢 Как снимать в помещении', callback_data='sheet_indoor'),
        InlineKeyboardButton('❓ ТОП вопросов для интервью', callback_data='sheet_questions'),
        InlineKeyboardButton('🤖 Закадровый текст с ИИ', callback_data='sheet_ai_text'),
        InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
    )
    return markup

# ========== МЕНЮ ССЫЛОК ==========
def links_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🌐 Сайт медиацентра', url=LINKS['site']),
        InlineKeyboardButton('📺 YouTube канал', url=LINKS['youtube']),
        InlineKeyboardButton('🎓 Платформа aXIS', url=LINKS['axis']),
        InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
    )
    return markup

# ========== МЕНЮ ТЕСТОВ ==========
def tests_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🎥 Операторское мастерство', callback_data='test_camera'),
        InlineKeyboardButton('📰 Журналистика', callback_data='test_journalism'),
        InlineKeyboardButton('🎬 Режиссура', callback_data='test_directing'),
        InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
    )
    return markup
