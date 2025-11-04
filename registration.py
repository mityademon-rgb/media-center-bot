"""
Процесс регистрации пользователя
"""
from database import create_user, get_user, update_user
from keyboards import main_menu, nickname_preference_keyboard
from gamification import add_xp

def start_registration(bot, message):
    """Начать процесс регистрации"""
    user_id = message.chat.id
    
    # Создаём нового пользователя с данными Telegram
    telegram_data = {
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name
    }
    create_user(user_id, telegram_data)
    
    # Устанавливаем шаг 1 - запрос имени и фамилии
    update_user(user_id, {'registration_step': 1})
    
    bot.send_message(
        user_id,
        "Йоу! 👋 Давай знакомиться!\n\n"
        "📝 Напиши своё *Имя и Фамилию* (через пробел)\n\n"
        "Например: Дмитрий Иванов",
        parse_mode='Markdown'
    )

def handle_registration_step(bot, message):
    """Обработать шаг регистрации"""
    user_id = message.chat.id
    user = get_user(user_id)
    
    if not user:
        start_registration(bot, message)
        return
    
    step = user.get('registration_step', 0)
    text = message.text.strip()
    
    # ШАГ 1: Имя и Фамилия
    if step == 1:
        parts = text.split()
        if len(parts) < 2:
            bot.send_message(
                user_id,
                "⚠️ Напиши *Имя и Фамилию через пробел*\n\n"
                "Например: Дмитрий Иванов",
                parse_mode='Markdown'
            )
            return
        
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        
        update_user(user_id, {
            'first_name': first_name,
            'last_name': last_name,
            'registration_step': 2
        })
        
        bot.send_message(
            user_id,
            f"Кайф, {first_name}! 🔥\n\n"
            f"🎮 А теперь придумай себе крутой *никнейм*!\n\n"
            f"Это может быть твой игровой ник, творческий псевдоним "
            f"или просто что-то стильное 😎\n\n"
            f"Давай, удивляй!",
            parse_mode='Markdown'
        )
    
    # ШАГ 2: Никнейм
    elif step == 2:
        if len(text) < 2:
            bot.send_message(user_id, "⚠️ Никнейм слишком короткий. Попробуй ещё раз:")
            return
        
        update_user(user_id, {
            'nickname': text,
            'registration_step': 3
        })
        
        bot.send_message(
            user_id,
            f"Воу! *{text}* - звучит огонь! 🚀\n\n"
            f"🎂 Скинь свой *возраст* (просто напиши число)",
            parse_mode='Markdown'
        )
    
    # ШАГ 3: Возраст
    elif step == 3:
        try:
            age = int(text)
            if age < 10 or age > 100:
                bot.send_message(user_id, "⚠️ Введи реальный возраст (10-100):")
                return
            
            update_user(user_id, {
                'age': age,
                'registration_step': 4
            })
            
            user = get_user(user_id)
            first_name = user.get('first_name', '')
            nickname = user.get('nickname', '')
            
            bot.send_message(
                user_id,
                "Окей! 👌\n\n"
                "💬 Как тебе больше зайдёт - чтобы я к тебе обращался "
                "*по имени* или *по нику*?\n\n"
                "Выбирай! 👇",
                parse_mode='Markdown',
                reply_markup=nickname_preference_keyboard(first_name, nickname)
            )
        except ValueError:
            bot.send_message(user_id, "⚠️ Введи возраст числом! Например: 16")
    
    # ШАГ 4: обрабатывается через callback (см. handle_nickname_preference)
    
    else:
        bot.send_message(
            user_id,
            "Что-то пошло не так 🤔\n\nДавай начнём сначала!"
        )
        start_registration(bot, message)

def handle_nickname_preference(bot, call):
    """Обработать выбор обращения (имя/ник)"""
    user_id = call.message.chat.id
    user = get_user(user_id)
    
    if not user or user.get('registration_step') != 4:
        bot.answer_callback_query(call.id, "⚠️ Что-то пошло не так")
        return
    
    # Определяем выбор
    use_nickname = call.data == 'prefer_nickname'
    display_name = user.get('nickname') if use_nickname else user.get('first_name')
    
    # Сохраняем выбор и завершаем базовую регистрацию
    update_user(user_id, {
        'use_nickname': use_nickname,
        'registration_step': 5
    })
    
    bot.answer_callback_query(call.id)
    
    # Удаляем клавиатуру
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass
    
    # Отправляем инструкцию про МосРег
    bot.send_message(
        user_id,
        f"Ну всё, {display_name}, погнали! 🎉\n\n"
        f"📚 Короче, занятия в медиацентре полностью *бесплатные* (да-да, за 0₽!), "
        f"но чтобы ты мог тусить на всех наших ивентах и не пропускать занятия, "
        f"нужно зарегаться на портале МосРег.\n\n"
        f"🎯 *ЧТО ДЕЛАТЬ:*\n\n"
        f"1️⃣ Тыкни на ссылку ниже 👇\n"
        f"2️⃣ Запишись в медиацентр (любая группа норм)\n"
        f"3️⃣ Подпиши договор (да, это быстро)\n"
        f"4️⃣ Жди свой персональный QR-код\n\n"
        f"📍 *ГДЕ ИСКАТЬ QR-КОД:*\n\n"
        f"Этот код будет на твоём личном бейдже 🎫\n"
        f"Найдёшь его в нижнем меню на сайте mosreg.ru\n"
        f"(типа там будет раздел с твоим профилем)\n\n"
        f"5️⃣ Сделай скрин или фото бейджа и *скинь мне!*\n\n"
        f"🔗 *ВОТ ССЫЛКА:*\n"
        f"https://dk.mosreg.ru/dk/marfino/workshops/804ce64a-bcbd-48ad-80cc-630f23d0c9dd\n\n"
        f"⏰ *ПО ВРЕМЕНИ:*\n"
        f"Код не сразу придёт, это норма! Сначала договор подпишешь, потом появится бейдж. "
        f"Может занять денёк-другой.\n\n"
        f"🤖 А пока можешь юзать бота! Я тебе потом напомню про код, не переживай 😉\n\n"
        f"Поехали! Жми /start и погнали! 🚀",
        parse_mode='Markdown'
    )

def handle_qr_code(bot, message):
    """Обработать отправку QR-кода"""
    user_id = message.chat.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(user_id, "⚠️ Сначала пройди регистрацию! Напиши /start")
        return
    
    # Проверяем что пользователь на шаге 5 (ожидание QR)
    if user.get('registration_step') != 5:
        bot.send_message(
            user_id,
            "📸 Спасибо за фото, но сейчас я его не жду 🤔\n\n"
            "Используй кнопки меню 👇",
            reply_markup=main_menu()
        )
        return
    
    # Получаем фото наибольшего размера
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Сохраняем QR-код
    update_user(user_id, {
        'qr_code': file_id,
        'registration_step': 6,  # Регистрация завершена!
        'qr_verified': False  # Ждёт проверки админом
    })
    
    # Даём бонус за регистрацию
    add_xp(user_id, 50, 'registration')
    
    display_name = get_user_display_name(user_id)
    
    bot.send_message(
        user_id,
        f"🎉 Отлично, {display_name}! Регистрация завершена!\n\n"
        f"📸 QR-код сохранён! Админ проверит его в ближайшее время.\n\n"
        f"💰 Ты получил *+50 XP* за регистрацию!\n\n"
        f"Теперь ты можешь:\n"
        f"• Смотреть расписание 📅\n"
        f"• Выполнять задания 📸\n"
        f"• Учить шпаргалки 📚\n"
        f"• Соревноваться в рейтинге 🏆\n\n"
        f"Используй кнопки меню! 👇",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )
    
    # Уведомляем админа о новом QR
    try:
        import os
        admin_id = int(os.environ.get('ADMIN_ID', 0))
        if admin_id:
            bot.send_message(
                admin_id,
                f"📸 *НОВЫЙ QR-КОД*\n\n"
                f"От: {user.get('first_name', '')} {user.get('last_name', '')}\n"
                f"Ник: {user.get('nickname', '—')}\n"
                f"Возраст: {user.get('age', '—')}\n"
                f"ID: `{user_id}`",
                parse_mode='Markdown'
            )
            bot.send_photo(admin_id, file_id)
    except Exception as e:
        print(f"⚠️ Не удалось уведомить админа: {e}")

def get_user_display_name(user_id):
    """Получить отображаемое имя (с учётом выбора имя/ник)"""
    user = get_user(user_id)
    if not user:
        return "друг"
    
    if user.get('use_nickname'):
        return user.get('nickname', user.get('first_name', 'друг'))
    else:
        return user.get('first_name', 'друг')

def send_qr_reminder(bot):
    """Отправить напоминание пользователям без QR-кода"""
    from database import get_all_users
    
    users = get_all_users()
    count = 0
    
    for user_id_str, user in users.items():
        # Проверяем: регистрация завершена (шаг >= 5), но нет QR-кода
        if user.get('registration_step', 0) >= 5 and not user.get('qr_code'):
            try:
                display_name = get_user_display_name(int(user_id_str))
                
                bot.send_message(
                    int(user_id_str),
                    f"👋 Привет, {display_name}!\n\n"
                    f"📸 Не забудь скинуть мне QR-код с бейджа МосРег!\n\n"
                    f"Это нужно для отметки посещений 📋\n\n"
                    f"Просто отправь мне фото или скриншот бейджа 👇"
                )
                count += 1
            except Exception as e:
                print(f"⚠️ Не удалось отправить напоминание {user_id_str}: {e}")
    
    print(f"✅ Отправлено {count} напоминаний о QR-коде")
    return count
