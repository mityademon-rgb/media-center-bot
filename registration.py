"""
Процесс регистрации пользователя
"""
from database import create_user, get_user, update_user
from keyboards import main_menu
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
    
    # Устанавливаем шаг 1 - запрос имени
    update_user(user_id, {'registration_step': 1})
    
    bot.send_message(
        user_id,
        "🎬 Йоу! Добро пожаловать в бот медиацентра!\n\n"
        "Давай познакомимся!\n\n"
        "Как тебя зовут? (напиши своё имя)"
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
    
    # ШАГ 1: Имя
    if step == 1:
        if len(text) < 2:
            bot.send_message(user_id, "⚠️ Имя слишком короткое. Попробуй ещё раз:")
            return
        
        update_user(user_id, {
            'first_name': text,
            'registration_step': 2
        })
        
        bot.send_message(
            user_id,
            f"Приятно познакомиться, {text}! 👋\n\n"
            f"А какая у тебя фамилия?"
        )
    
    # ШАГ 2: Фамилия
    elif step == 2:
        if len(text) < 2:
            bot.send_message(user_id, "⚠️ Фамилия слишком короткая. Попробуй ещё раз:")
            return
        
        update_user(user_id, {
            'last_name': text,
            'registration_step': 3
        })
        
        bot.send_message(
            user_id,
            "Отлично! 👌\n\n"
            "В какой ты группе?\n"
            "(напиши номер или название группы)"
        )
    
    # ШАГ 3: Группа
    elif step == 3:
        update_user(user_id, {
            'group': text,
            'registration_step': 4
        })
        
        bot.send_message(
            user_id,
            "Супер! 🔥\n\n"
            "Какое у тебя направление?\n\n"
            "Например:\n"
            "• Режиссура 🎬\n"
            "• Операторское дело 🎥\n"
            "• Монтаж ✂️\n"
            "• Журналистика 📰\n"
            "• Или что-то другое?"
        )
    
    # ШАГ 4: Направление
    elif step == 4:
        update_user(user_id, {
            'direction': text,
            'registration_step': 5
        })
        
        user = get_user(user_id)
        first_name = user.get('first_name', 'друг')
        
        bot.send_message(
            user_id,
            f"Круто, {first_name}! 🎉\n\n"
            f"Последний шаг!\n\n"
            f"📸 Скинь мне фото или скриншот твоего QR-кода с бейджа МосРег.\n\n"
            f"Это нужно для отметки посещений.\n\n"
            f"⚠️ Если у тебя пока нет QR - не страшно! "
            f"Скинешь потом, но пока можешь юзать бота 👇"
        )
    
    else:
        bot.send_message(
            user_id,
            "Что-то пошло не так 🤔\n\nДавай начнём сначала!",
            reply_markup=main_menu()
        )
        start_registration(bot, message)

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
    xp_result = add_xp(user_id, 50, 'registration')
    
    first_name = user.get('first_name', 'друг')
    
    bot.send_message(
        user_id,
        f"🎉 Отлично, {first_name}! Регистрация завершена!\n\n"
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
                f"От: {first_name} {user.get('last_name', '')}\n"
                f"Группа: {user.get('group', '—')}\n"
                f"Направление: {user.get('direction', '—')}\n"
                f"ID: `{user_id}`",
                parse_mode='Markdown'
            )
            bot.send_photo(admin_id, file_id)
    except Exception as e:
        print(f"⚠️ Не удалось уведомить админа: {e}")

def skip_qr_code(bot, user_id):
    """Пропустить отправку QR-кода"""
    user = get_user(user_id)
    
    if not user or user.get('registration_step') != 5:
        return False
    
    # Завершаем регистрацию без QR
    update_user(user_id, {
        'registration_step': 6,
        'qr_code': None,
        'qr_verified': False
    })
    
    # Даём бонус за регистрацию
    add_xp(user_id, 50, 'registration')
    
    first_name = user.get('first_name', 'друг')
    
    bot.send_message(
        user_id,
        f"✅ Окей, {first_name}! Регистрация завершена!\n\n"
        f"📸 Когда будет QR-код - скинь мне его в любое время.\n\n"
        f"💰 Ты получил *+50 XP* за регистрацию!\n\n"
        f"А пока можешь юзать бота! 👇",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )
    
    return True

def send_qr_reminder(bot):
    """Отправить напоминание пользователям без QR-кода"""
    from database import get_all_users
    
    users = get_all_users()
    count = 0
    
    for user_id_str, user in users.items():
        # Проверяем: регистрация завершена, но нет QR-кода
        if user.get('registration_step') == 6 and not user.get('qr_code'):
            try:
                first_name = user.get('first_name', 'друг')
                
                bot.send_message(
                    int(user_id_str),
                    f"👋 Привет, {first_name}!\n\n"
                    f"📸 Не забудь скинуть мне QR-код с бейджа МосРег!\n\n"
                    f"Это нужно для отметки посещений 📋\n\n"
                    f"Просто отправь мне фото или скриншот бейджа 👇"
                )
                count += 1
            except Exception as e:
                print(f"⚠️ Не удалось отправить напоминание {user_id_str}: {e}")
    
    print(f"✅ Отправлено {count} напоминаний о QR-коде")
    return count
