"""
Процесс регистрации пользователей
"""
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from database import get_user, update_user, create_user, get_user_display_name
from datetime import datetime
from config import LINKS

def start_registration(bot, message):
    """Начать регистрацию"""
    user_id = message.chat.id
    create_user(user_id)
    
    bot.send_message(
        user_id,
        "👋 Привет! Давай познакомимся!\n\n"
        "📝 Напиши своё *Имя и Фамилию* (через пробел)\n\n"
        "Например: Дмитрий Иванов",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )

def handle_registration_step(bot, message):
    """Обработка шагов регистрации"""
    user_id = message.chat.id
    user = get_user(user_id)
    
    if not user:
        start_registration(bot, message)
        return
    
    step = user.get('registration_step', 1)
    
    # ШАГ 1: Имя и Фамилия
    if step == 1:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            bot.send_message(
                user_id,
                "❌ Напиши Имя и Фамилию через пробел\n\n"
                "Например: Дмитрий Иванов"
            )
            return
        
        first_name, last_name = parts[0], parts[1]
        update_user(user_id, 
                   first_name=first_name,
                   last_name=last_name,
                   registration_step=2)
        
        bot.send_message(
            user_id,
            f"✅ Отлично, {first_name}!\n\n"
            "🎮 Теперь придумай себе *никнейм*\n\n"
            "Это может быть игровой ник, творческий псевдоним или просто красивое слово 😊",
            parse_mode='Markdown'
        )
    
    # ШАГ 2: Никнейм
    elif step == 2:
        nickname = message.text.strip()
        if len(nickname) < 2:
            bot.send_message(user_id, "❌ Никнейм слишком короткий. Попробуй ещё раз!")
            return
        
        update_user(user_id, 
                   nickname=nickname,
                   registration_step=3)
        
        bot.send_message(
            user_id,
            f"🎯 Круто! Никнейм *{nickname}* мне нравится!\n\n"
            "🎂 Сколько тебе лет? (просто напиши число)",
            parse_mode='Markdown'
        )
    
    # ШАГ 3: Возраст
    elif step == 3:
        try:
            age = int(message.text.strip())
            if age < 6 or age > 100:
                bot.send_message(user_id, "🤔 Кажется, ты ошибся. Напиши свой реальный возраст")
                return
        except ValueError:
            bot.send_message(user_id, "❌ Напиши просто число (например: 15)")
            return
        
        user = update_user(user_id, 
                          age=age,
                          registration_step=4)
        
        # Кнопки выбора обращения
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            KeyboardButton(f"По имени ({user['first_name']})"),
            KeyboardButton(f"По никнейму ({user['nickname']})")
        )
        
        bot.send_message(
            user_id,
            "💬 Как тебе удобнее, чтобы я к тебе обращался?\n\n"
            "Выбери вариант:",
            reply_markup=markup
        )
    
    # ШАГ 4: Выбор обращения
    elif step == 4:
        text = message.text.lower()
        user = get_user(user_id)
        
        if 'имени' in text or 'имя' in text:
            prefer = 'name'
            display_name = user['first_name']
        elif 'нику' in text or 'никнейм' in text:
            prefer = 'nickname'
            display_name = user['nickname']
        else:
            bot.send_message(user_id, "❌ Используй кнопки для выбора")
            return
        
        update_user(user_id,
                   prefer_name=prefer,
                   registration_step=5,
                   qr_requested_at=datetime.now().isoformat())
        
        # ФИНАЛЬНОЕ СООБЩЕНИЕ С ИНСТРУКЦИЕЙ
        portal_link = "https://dk.mosreg.ru/dk/marfino/workshops/804ce64a-bcbd-48ad-80cc-630f23d0c9dd"
        
        bot.send_message(
            user_id,
            f"🎉 Супер, {display_name}!\n\n"
            f"📚 Твои занятия в медиацентре *абсолютно бесплатные*, но для того, "
            f"чтобы ты смог посещать их и участвовать во всех мероприятиях, "
            f"нужно пройти регистрацию на портале МосРег.\n\n"
            f"📝 *ЧТО НУЖНО СДЕЛАТЬ:*\n\n"
            f"1️⃣ Перейди по ссылке ниже\n"
            f"2️⃣ Запишись в медиацентр (выбери любую группу)\n"
            f"3️⃣ После регистрации тебе выдадут персональный QR-код\n"
            f"4️⃣ Пришли мне этот QR-код (фото или скриншот)\n\n"
            f"🔗 *ССЫЛКА ДЛЯ РЕГИСТРАЦИИ:*\n"
            f"{portal_link}\n\n"
            f"⚠️ *ВАЖНО:* Код приходит не сразу! Нужно подписать договор, "
            f"а потом придёт код.\n\n"
            f"🤖 Пока можешь пользоваться ботом, а чуть позже я напомню тебе про код!\n\n"
            f"✅ Жми /start чтобы начать!",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )

def handle_qr_code(bot, message):
    """Обработка полученного QR-кода"""
    user_id = message.chat.id
    user = get_user(user_id)
    
    if not user:
        return
    
    # Проверяем, что это фото
    if message.photo:
        file_id = message.photo[-1].file_id
        
        update_user(user_id,
                   qr_code=file_id,
                   is_registered=True,
                   registration_step=999)  # Регистрация завершена
        
        display_name = get_user_display_name(user_id)
        
        bot.send_message(
            user_id,
            f"✅ Отлично, {display_name}! QR-код получен!\n\n"
            f"🎉 *Регистрация завершена!*\n\n"
            f"Теперь у тебя есть доступ ко всем функциям бота!\n\n"
            f"Жми /start чтобы начать! 🚀",
            parse_mode='Markdown'
        )
        
        # Уведомление админу
        from config import ADMIN_ID
        bot.send_message(
            ADMIN_ID,
            f"✅ Новый пользователь зарегистрирован!\n\n"
            f"Имя: {user['first_name']} {user['last_name']}\n"
            f"Никнейм: {user['nickname']}\n"
            f"Возраст: {user['age']}\n"
            f"ID: {user_id}",
            parse_mode='Markdown'
        )
        
        # Отправляем админу QR-код
        bot.send_photo(ADMIN_ID, file_id, caption=f"QR-код пользователя {user['first_name']}")

def send_qr_reminder(bot, user_data):
    """Отправить напоминание о QR-коде"""
    user_id = user_data['user_id']
    display_name = get_user_display_name(user_id)
    
    update_user(user_id, qr_reminder_sent=True)
    
    bot.send_message(
        user_id,
        f"👋 {display_name}, привет!\n\n"
        f"📸 Жду твой QR-код с портала МосРег\n\n"
        f"Он уже пришёл? Пришли мне фото или скриншот!\n\n"
        f"Если ещё нет - ничего страшного, жди письмо от портала 📧",
        parse_mode='Markdown'
    )
