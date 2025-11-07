"""
ВСЕ КЛАВИАТУРЫ БОТА
"""
from telebot import types

# === ПОСТОЯННАЯ КЛАВИАТУРА ВНИЗУ (ReplyKeyboard) ===

def main_reply_keyboard():
    """Главное меню (постоянная клавиатура внизу)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
    
        types.KeyboardButton("📅 Расписание"),
        types.KeyboardButton("🎯 Задания"),
        types.KeyboardButton("👤 Профиль"),
        types.KeyboardButton("📊 Прогресс"),
       types.KeyboardButton("🤖 AI-Помощник"),
        types.KeyboardButton("❓ Помощь")
    ]
    
    markup.add(*buttons)
    return markup


# === РЕГИСТРАЦИЯ (InlineKeyboard - остаётся) ===

def nickname_preference_keyboard(first_name, nickname):
    """Клавиатура выбора: по имени или по нику"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_name = types.InlineKeyboardButton(
        f"👤 {first_name}",
        callback_data="use_name"
    )
    
    btn_nickname = types.InlineKeyboardButton(
        f"🎮 {nickname}",
        callback_data="use_nickname"
    )
    
    markup.add(btn_name, btn_nickname)
    return markup


# === ГЛАВНОЕ МЕНЮ (InlineKeyboard - для callback) ===

def main_menu_keyboard():
    """Главное меню (inline кнопки)"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        
        types.InlineKeyboardButton("📅 Расписание", callback_data="schedule"),
        types.InlineKeyboardButton("🎯 Задания", callback_data="tasks"),
        types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        types.InlineKeyboardButton("📊 Мой прогресс", callback_data="my_stats"),
        types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    ]
    
    markup.add(*buttons)
    return markup


# === ШПАРГАЛКИ ===

def cheatsheets_keyboard():
    """Меню шпаргалок"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("📸 Фото", callback_data="cheat_photo"),
        types.InlineKeyboardButton("🎬 Видео", callback_data="cheat_video"),
        types.InlineKeyboardButton("🎨 Дизайн", callback_data="cheat_design"),
        types.InlineKeyboardButton("✂️ Монтаж", callback_data="cheat_editing"),
        types.InlineKeyboardButton("🎤 Звук", callback_data="cheat_sound"),
        types.InlineKeyboardButton("📱 SMM", callback_data="cheat_smm"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    ]
    
    markup.add(*buttons)
    return markup


# === ПРОФИЛЬ ===

def profile_keyboard():
    """Меню профиля"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("✏️ Изменить имя", callback_data="edit_name"),
        types.InlineKeyboardButton("🎮 Изменить ник", callback_data="edit_nickname"),
        types.InlineKeyboardButton("💬 Изменить обращение", callback_data="edit_preference"),
        types.InlineKeyboardButton("🎫 Загрузить QR", callback_data="upload_qr"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    ]
    
    markup.add(*buttons)
    return markup


# === РАСПИСАНИЕ ===

def schedule_keyboard():
    """Меню расписания"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("📅 На эту неделю", callback_data="schedule_week"),
        types.InlineKeyboardButton("📆 На месяц", callback_data="schedule_month"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    ]
    
    markup.add(*buttons)
    return markup


# === ЗАДАНИЯ ===

def tasks_keyboard():
    """Меню заданий"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("📋 Активные", callback_data="tasks_active"),
        types.InlineKeyboardButton("✅ Выполненные", callback_data="tasks_completed"),
        types.InlineKeyboardButton("🎯 Получить новое", callback_data="tasks_new"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    ]
    
    markup.add(*buttons)
    return markup


# === АДМИНКА ===

def admin_keyboard():
    """Меню админа"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("📥 Экспорт базы", callback_data="admin_export_db"),
        types.InlineKeyboardButton("⏳ Без QR-кода", callback_data="admin_without_qr"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("✉️ Рассылка", callback_data="admin_broadcast")
    ]
    
    markup.add(*buttons)
    return markup


# === ПОДТВЕРЖДЕНИЕ ===

def confirm_keyboard(action):
    """Клавиатура подтверждения действия"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_yes = types.InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}")
    btn_no = types.InlineKeyboardButton("❌ Нет", callback_data=f"cancel_{action}")
    
    markup.add(btn_yes, btn_no)
    return markup


# === НАЗАД В МЕНЮ ===

def back_to_menu_keyboard():
    """Простая кнопка назад"""
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")
    markup.add(btn_back)
    return markup
