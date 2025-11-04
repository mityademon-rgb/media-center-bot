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
        "Йоу! 👋 Давай знакомиться!\n\n"
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
                "Эй, напиши Имя и Фамилию через пробел! 😅\n\n"
                "Вот так: Дмитрий Иванов"
            )
            return
        
        first_name, last_name = parts[0], parts[1]
        update_user(user_id, 
                   first_name=first_name,
                   last_name=last_name,
                   registration_step=2)
        
        bot.send_message(
            user_id,
            f"Кайф, {first_name}! 🔥\n\n"
            "🎮 А теперь придумай себе *крутой никнейм*!\n\n"
            "Это может быть твой игровой ник, творческий псевдоним "
            "или просто что-то стильное 😎\n\n"
            "Давай, удивляй!",
            parse_mode='Markdown'
        )
    
    # ШАГ 2: Никнейм
    elif step == 2:
        nickname = message.text.strip()
        if len(nickname) < 2:
            bot.send_message(user_id, "Слишком коротко! 🤔 Придумай что-нибудь покруче!")
            return
        
        update_user(user_id, 
                   nickname=nickname,
                   registration_step=3)
        
        bot.send_message(
            user_id,
            f"Воу! *{nickname}* - звучит огонь! 🚀\n\n"
            "🎂 Скинь свой возраст (просто напиши число)",
            parse_mode='Markdown'
        )
    
    # ШАГ 3: Возраст
    elif step == 3:
        try:
            age = int(message.text.strip())
            if age < 6 or age > 100:
                bot.send_message(user_id, "Хм, что-то не то 🤔 Напиши свой реальный возраст")
                return
        except ValueError:
            bot.send_message(user_id, "Напиши просто циферку! Например: 15")
            return
        
        user = update_user(user_id, 
                          age=age,
                          registration_step=4)
        
        # Кнопки выбора обращения
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            KeyboardButton(f"По имени ({user['first_name']})"),
            KeyboardButton(f"По нику ({user['nickname']})")
        )
        
        bot.send_message(
            user_id,
            "Окей! 👌\n\n"
            "💬 Как тебе больше зайдёт - чтобы я к тебе обращался по имени или по нику?\n\n"
            "Выбирай! 👇",
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
            bot.send_message(user_id, "Эй! Используй кнопки, которые я отправил! 👆")
            return
        
        update_user(user_id,
                   prefer_name=prefer,
                   registration_step=5,
                   qr_requested_at=datetime.now().isoformat())
        
        # ФИНАЛЬНОЕ СООБЩЕНИЕ С ИНСТРУКЦИЕЙ
        portal_link = "https://dk.mosreg.ru/dk/marfino/workshops/804ce64a-bcbd-48ad-80cc-630f23d0c9dd"
        
        bot.send_message(
            user_id,
            f"Ну всё, {display_name}, погнали! 🎉\n\n"
            f"📚 Короче, занятия в медиацентре *полностью бесплатные* (да-да, за 0₽!), "
            f"но чтобы ты мог тусить на всех наших ивентах и не пропускать занятия, "
            f"нужно зарегаться на портале МосРег.\n\n"
            f"🎯 *ЧТО ДЕЛАТЬ:*\n\n"
            f"1️⃣ Тыкни на ссылку ниже 👇\n"
            f"2️⃣ Запишись в медиацентр (любая группа норм)\n"
            f"3️⃣ Подпиши договор (да, это быстро)\n"
            f"4️⃣ Жди свой персональный QR-код\n\n"
            f"📍 *ГДЕ ИСКАТЬ QR-КОД:*\n\n"
            f"Этот код будет на твоём *личном бейдже* 🎫\n"
            f"Найдёшь его в *нижнем меню* на сайте mosreg.ru\n"
            f"(типа там будет раздел с твоим профилем)\n\n"
            f"5️⃣ Сделай скрин или фото бейджа и скинь мне!\n\n"
            f"🔗 *ВОТ ССЫЛКА:*\n"
            f"{portal_link}\n\n"
            f"⏰ *ПО ВРЕМЕНИ:*\n"
            f"Код не сразу придёт, это норма! Сначала договор подпишешь, "
            f"потом появится бейдж. Может занять денёк-другой.\n\n"
            f"🤖 А пока можешь юзать бота! Я тебе потом напомню про код, не переживай 😉\n\n"
            f"Поехали! Жми /start и погнали! 🚀",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Уведомление админу о начале регистрации
        from admin import notify_admin_new_user
        notify_admin_new_user(bot, user)

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
            f"Ееее, {display_name}! 🔥 QR-код получил!\n\n"
            f"🎉 *РЕГИСТРАЦИЯ ЗАВЕРШЕНА!* 🎉\n\n"
            f"Теперь у тебя полный доступ ко всему! \n\n"
            f"Давай, жми /start и погнали творить! 🚀",
            parse_mode='Markdown'
        )
        
        # Получаем обновлённые данные пользователя
        user = get_user(user_id)
        
        # Уведомление админу с QR-кодом
        from admin import notify_admin_new_user
        notify_admin_new_user(bot, user, file_id)

def send_qr_reminder(bot, user_data):
    """Отправить напоминание о QR-коде"""
    user_id = user_data['user_id']
    display_name = get_user_display_name(user_id)
    
    update_user(user_id, qr_reminder_sent=True)
    
    bot.send_message(
        user_id,
        f"Йоу, {display_name}! 👋\n\n"
        f"📸 Где твой QR-код с портала МосРег? Я жду! 😎\n\n"
        f"*Как найти:*\n\n"
        f"1️⃣ Зайди на mosreg.ru\n"
        f"2️⃣ В *нижнем меню* найди свой бейдж\n"
        f"3️⃣ Там увидишь QR-код\n"
        f"4️⃣ Сделай скрин и кинь мне!\n\n"
        f"Если бейдж ещё не появился - всё окей, просто подожди ещё чуть-чуть "
        f"и проверь попозже 📧\n\n"
        f"Жду! 🔥",
        parse_mode='Markdown'
    )
