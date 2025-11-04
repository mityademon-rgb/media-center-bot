"""
БЛОК 1: ЛОГИКА РЕГИСТРАЦИИ
Шаги: Имя → Никнейм → Возраст → QR-инструкция
"""
import re
from datetime import datetime
from database import get_user, create_user, update_user, get_user_display_name

def handle_start_registration(bot, message):
    """Начать регистрацию"""
    user_id = message.from_user.id
    
    # Создаём пользователя если нет
    user = get_user(user_id)
    if not user:
        telegram_data = {
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }
        user = create_user(user_id, telegram_data)
    
    # Приветствие
    welcome_text = """
Йоу! 👋 Я твой помощник и друг, который должен быть всегда под рукой!

Со мной ты:
• Никогда не забудешь что взять на съёмку 📸
• Сможешь задать любые вопросы 💬
• Узнаешь о занятиях медиацентра 📚
• И многое другое! 🚀

Для начала давай знакомиться! 

📝 Напиши своё **Имя и Фамилию** (через пробел)

_Например:_ Дмитрий Иванов
"""
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    
    # Устанавливаем шаг 1
    update_user(user_id, {'registration_step': 1})

def handle_registration_step(bot, message):
    """Роутер по шагам регистрации"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        return handle_start_registration(bot, message)
    
    step = user.get('registration_step', 0)
    
    if step == 1:
        return handle_name(bot, message)
    elif step == 2:
        return handle_nickname(bot, message)
    elif step == 3:
        return handle_age(bot, message)

def handle_name(bot, message):
    """Шаг 1: Имя и Фамилия"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Валидация: 2 слова, только буквы
    parts = text.split()
    
    if len(parts) < 2:
        bot.send_message(
            message.chat.id,
            "⚠️ Напиши Имя И Фамилию через пробел\n\nНапример: Дмитрий Иванов"
        )
        return
    
    # Проверяем что только буквы (кириллица или латиница)
    name_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\-]+$')
    
    if not all(name_pattern.match(part) for part in parts[:2]):
        bot.send_message(
            message.chat.id,
            "⚠️ Используй только буквы (без цифр и спецсимволов)\n\nПопробуй ещё раз:"
        )
        return
    
    first_name = parts[0].capitalize()
    last_name = parts[1].capitalize()
    
    # Сохраняем
    update_user(user_id, {
        'first_name': first_name,
        'last_name': last_name,
        'registration_step': 2
    })
    
    # Следующий шаг
    bot.send_message(
        message.chat.id,
        f"Кайф, {first_name}! 🔥\n\n"
        "🎮 А теперь придумай себе крутой **никнейм**!\n\n"
        "Это может быть твой игровой ник, творческий псевдоним или просто что-то стильное 😎\n\n"
        "Давай, удивляй!",
        parse_mode='Markdown'
    )

def handle_nickname(bot, message):
    """Шаг 2: Никнейм"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Валидация: 3-20 символов
    if len(text) < 3:
        bot.send_message(
            message.chat.id,
            "⚠️ Никнейм слишком короткий (минимум 3 символа)\n\nПопробуй другой:"
        )
        return
    
    if len(text) > 20:
        bot.send_message(
            message.chat.id,
            "⚠️ Никнейм слишком длинный (максимум 20 символов)\n\nПопробуй покороче:"
        )
        return
    
    # Сохраняем
    update_user(user_id, {
        'nickname': text,
        'registration_step': 3
    })
    
    # Следующий шаг
    bot.send_message(
        message.chat.id,
        f"Воу! **{text}** - звучит огонь! 🚀\n\n"
        "🎂 Скинь свой возраст (просто напиши число)",
        parse_mode='Markdown'
    )

def handle_age(bot, message):
    """Шаг 3: Возраст"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Валидация: число 10-100
    try:
        age = int(text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "⚠️ Напиши число (твой возраст)\n\nПопробуй ещё раз:"
        )
        return
    
    if age < 10 or age > 100:
        bot.send_message(
            message.chat.id,
            "⚠️ Введи реальный возраст (10-100):"
        )
        return
    
    # Сохраняем (регистрация завершена - шаг 5!)
    user = get_user(user_id)
    update_user(user_id, {
        'age': age,
        'use_nickname': False,  # По умолчанию по имени
        'registration_step': 5  # Регистрация завершена!
    })
    
    # Инструкция про QR-код
    qr_text = """
Ну всё, погнали! 🎉

📚 Короче, занятия в медиацентре полностью **бесплатные** (да-да, за 0₽!), но чтобы ты мог тусить на всех наших ивентах и не пропускать занятия, нужно зарегаться на портале МосРег.

🎯 **ЧТО ДЕЛАТЬ:**

1️⃣ Тыкни на ссылку ниже 👇
2️⃣ Запишись в медиацентр (любая группа норм)
3️⃣ Подпиши договор (да, это быстро)
4️⃣ Жди свой персональный QR-код

📍 **ГДЕ ИСКАТЬ QR-КОД:**

Этот код будет на твоём личном бейдже 🎫
Найдёшь его в нижнем меню на сайте mosreg.ru
(типа там будет раздел с твоим профилем)

5️⃣ Сделай скрин или фото бейджа и скинь мне!

🔗 **ВОТ ССЫЛКА:**
https://dk.mosreg.ru/dk/marfino/workshops/804ce64a-bcbd-48ad-80cc-630f23d0c9dd

⏰ **ПО ВРЕМЕНИ:**
Код не сразу придёт, это норма! Сначала договор подпишешь, потом появится бейдж. Может занять денёк-другой.

🤖 А пока можешь юзать бота! Я тебе потом напомню про код, не переживай 😉

Поехали! Жми /start и погнали! 🚀
"""
    
    bot.send_message(message.chat.id, qr_text, parse_mode='Markdown')

def handle_qr_photo(bot, message):
    """Обработка фото QR-кода"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user or user.get('registration_step', 0) < 5:
        return
    
    # Сохраняем file_id фото
    photo_file_id = message.photo[-1].file_id
    
    update_user(user_id, {
        'qr_code': photo_file_id,
        'qr_uploaded_at': datetime.now().isoformat()
    })
    
    display_name = get_user_display_name(user_id)
    
    bot.send_message(
        message.chat.id,
        f"Супер, {display_name}! 🎉\n\n"
        "✅ QR-код сохранён!\n\n"
        "Теперь ты можешь полноценно пользоваться ботом! Жми /start 🚀"
    )


# === НАПОМИНАНИЕ О QR-КОДЕ ===

def send_qr_reminder(bot):
    """Отправить напоминание о QR-коде пользователям без него"""
    from database import get_waiting_qr_users
    
    waiting_users = get_waiting_qr_users()
    
    if not waiting_users:
        print("✅ Все пользователи с QR-кодами")
        return
    
    reminder_text = """
👋 Привет, {name}!

Напоминаю, что тебе нужно загрузить QR-код с бейджа 🎫

📍 **Где найти:**
1. Зайди на https://dk.mosreg.ru
2. Открой свой профиль (нижнее меню)
3. Найди раздел с бейджем
4. Сделай скриншот и скинь мне!

🔗 **Ссылка для регистрации:**
https://dk.mosreg.ru/dk/marfino/workshops/804ce64a-bcbd-48ad-80cc-630f23d0c9dd

Как загрузишь - сразу получишь полный доступ к боту! 🚀
"""
    
    sent_count = 0
    
    for user in waiting_users:
        try:
            user_id = user['user_id']
            display_name = get_user_display_name(user_id)
            
            personalized_text = reminder_text.format(name=display_name)
            
            bot.send_message(user_id, personalized_text, parse_mode='Markdown')
            sent_count += 1
            
        except Exception as e:
            print(f"⚠️ Не удалось отправить напоминание {user_id}: {e}")
    
    print(f"✅ Отправлено {sent_count} напоминаний о QR-коде")


# Заглушки для обратной совместимости (если где-то импортируются)
def handle_nickname_preference(bot, call):
    """Заглушка - больше не используется"""
    pass
