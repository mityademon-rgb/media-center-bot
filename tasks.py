"""
СИСТЕМА ЗАДАНИЙ
Прогрессия, задания, награды
"""
from database import get_user, update_user
from datetime import datetime, timedelta
import telebot

# ============================================
# БАЗА ЗАДАНИЙ
# ============================================

TASKS_DATABASE = [
    # === УРОВЕНЬ 1 (Первые 4 задания) ===
    {
        'id': 'task_001',
        'title': '📱 Первый портрет',
        'description': 'Сфотографируй портрет мамы, папы или друга на телефон',
        'instructions': '''✨ Что нужно:
• Правило третей (глаза на верхней линии)
• Естественный свет (у окна)
• Чистый фон
• Модель смотрит в камеру или чуть в сторону

📸 Что загрузить:
Загрузи фото и напиши: где снимал, какой свет использовал, что получилось/не получилось''',
        'type': 'photo',
        'xp_reward': 50,
        'required_level': 1,
        'unlock_date': '2024-11-12',
        'order': 1
    },
    {
        'id': 'task_002',
        'title': '🎥 Первый ролик',
        'description': 'Сними короткое видео (15-30 сек) "Мой день"',
        'instructions': '''🎬 Требования:
• 3-5 разных планов
• Горизонтальная ориентация
• Стабильная картинка (держи телефон двумя руками)
• Хорошее освещение

📹 Что загрузить:
Загрузи видео и напиши: что снимал, сколько дублей сделал''',
        'type': 'video',
        'xp_reward': 75,
        'required_level': 1,
        'unlock_date': '2024-11-14',
        'order': 2
    },
    {
        'id': 'task_003',
        'title': '🤖 Знакомство с AI',
        'description': 'Попроси ChatGPT написать сценарий 30-сек ролика про школу',
        'instructions': '''💡 Что делать:
1. Зайди в ChatGPT (chat.openai.com) или Claude
2. Напиши промпт: "Напиши сценарий 30-секундного видео про один день в школе. С описанием каждой сцены"
3. Сохрани результат

📝 Что загрузить:
Скопируй и отправь боту: твой промпт и ответ AI (скриншот или текст)''',
        'type': 'ai',
        'xp_reward': 45,
        'required_level': 1,
        'unlock_date': '2024-11-16',
        'order': 3,
        'ai_prompt_example': 'Напиши сценарий 30-секундного видео про один день в школе'
    },
    {
        'id': 'task_004',
        'title': '📸 Правило третей',
        'description': 'Сделай 3 фото с правилом третей',
        'instructions': '''📐 Задание:
Сделай 3 фотографии разных объектов:
• Включи сетку на камере телефона
• Размести главный объект на пересечении линий
• Разные сюжеты (человек, предмет, пейзаж)

📸 Что загрузить:
3 фотографии + текст: что снимал и как использовал правило третей''',
        'type': 'photo',
        'xp_reward': 60,
        'required_level': 1,
        'unlock_date': '2024-11-18',
        'order': 4
    },
    
    # === УРОВЕНЬ 2 (5-9 задания) - выбор появляется ===
    {
        'id': 'task_005',
        'title': '🎬 Монтаж в CapCut',
        'description': 'Смонтируй видео из 5+ кадров с музыкой',
        'instructions': '''✂️ Требования:
• Скачай CapCut на телефон
• Собери 5-7 видеофрагментов (можно из галереи)
• Добавь переходы между кадрами
• Наложи музыку
• Длина: 30-60 секунд

🎥 Что загрузить:
Готовое видео + опиши: какие переходы использовал, почему выбрал эту музыку''',
        'type': 'video',
        'xp_reward': 90,
        'required_level': 2,
        'unlock_date': '2024-11-20',
        'order': 5,
        'choice_group': 1  # Группа выбора
    },
    {
        'id': 'task_006',
        'title': '📸 Фотосерия',
        'description': 'Создай серию из 4-5 фото на одну тему',
        'instructions': '''📷 Задание:
Выбери тему: "Утро", "Дорога в школу", "Мой район" и т.д.
• 4-5 фотографий
• Единый стиль
• Рассказывают историю

📸 Что загрузить:
Все фото + текст: какую тему выбрал, какую историю хотел рассказать''',
        'type': 'photo',
        'xp_reward': 85,
        'required_level': 2,
        'unlock_date': '2024-11-20',
        'order': 6,
        'choice_group': 1  # Та же группа - можно выбрать одно из двух
    },
    {
        'id': 'task_007',
        'title': '🤖 AI-редактор текста',
        'description': 'Используй AI для написания поста для соцсетей',
        'instructions': '''✍️ Задание:
1. Придумай тему поста (о школе, хобби, событии)
2. Попроси AI написать пост (100-150 слов)
3. Отредактируй результат своими словами
4. Попроси AI улучшить твою версию

📝 Что загрузить:
• Исходный промпт
• Первый ответ AI
• Твоя отредактированная версия
• Финальная версия после AI''',
        'type': 'ai',
        'xp_reward': 70,
        'required_level': 2,
        'unlock_date': '2024-11-22',
        'order': 7,
        'ai_prompt_example': 'Напиши пост на 120 слов про школьное мероприятие'
    },
    {
        'id': 'task_008',
        'title': '🎥 Интервью',
        'description': 'Сними короткое интервью (1-2 минуты)',
        'instructions': '''🎤 Задание:
Возьми интервью у друга/родителя:
• Подготовь 3-4 вопроса
• Сними горизонтально
• Хороший звук (не шумно, близко к собеседнику)
• Крупный план

🎥 Что загрузить:
Видео интервью + текст: кого снимал, какие вопросы задавал''',
        'type': 'video',
        'xp_reward': 95,
        'required_level': 2,
        'unlock_date': '2024-11-24',
        'order': 8,
        'choice_group': 2
    },
    {
        'id': 'task_009',
        'title': '📸 Репортаж',
        'description': 'Сделай фоторепортаж с мероприятия (5-7 фото)',
        'instructions': '''📷 Задание:
Сфотографируй любое событие (урок, перемена, секция):
• 5-7 фотографий
• Общие планы + крупные детали
• Люди в действии
• Эмоции

📸 Что загрузить:
Все фото + текст: что за событие, что старался показать''',
        'type': 'photo',
        'xp_reward': 90,
        'required_level': 2,
        'unlock_date': '2024-11-24',
        'order': 9,
        'choice_group': 2
    },
    
    # === УРОВЕНЬ 3+ (свободный выбор) ===
    {
        'id': 'task_010',
        'title': '🎬 Короткометражка',
        'description': 'Сними мини-фильм 1-3 минуты по сценарию',
        'instructions': '''🎥 Большой проект:
• Придумай простую историю (можно с AI)
• Напиши сценарий (5-10 сцен)
• Сними и смонтируй
• Добавь музыку/звуки
• Титры в начале/конце

🎬 Что загрузить:
Видео + сценарий в тексте + описание процесса''',
        'type': 'video',
        'xp_reward': 150,
        'required_level': 3,
        'unlock_date': '2024-11-26',
        'order': 10
    },
    {
        'id': 'task_011',
        'title': '🤖 AI-помощник оператора',
        'description': 'Используй AI для планирования съёмки',
        'instructions': '''💡 Задание:
1. Опиши AI какое видео хочешь снять
2. Попроси составить shot list (список планов)
3. Попроси советы по свету и композиции
4. Сними видео по этому плану

📝 Что загрузить:
• Переписка с AI (скрины)
• Готовое видео
• Анализ: что помогло, что изменил''',
        'type': 'ai',
        'xp_reward': 120,
        'required_level': 3,
        'unlock_date': '2024-11-28',
        'order': 11
    },
]

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_progress(user_id):
    """Получить прогресс пользователя"""
    user = get_user(user_id)
    
    level = user.get('level', 1)
    xp = user.get('xp', 0)
    completed = user.get('completed_tasks', [])
    
    # XP до следующего уровня
    xp_for_next = 100 - (xp % 100)
    
    # Доступные задания
    available = get_available_tasks(user_id)
    
    return {
        'level': level,
        'xp': xp,
        'xp_to_next': xp_for_next,
        'completed_tasks': completed,
        'completed_count': len(completed),
        'available_tasks': available,
        'available_count': len(available)
    }


def get_available_tasks(user_id):
    """Получить доступные задания для пользователя"""
    user = get_user(user_id)
    level = user.get('level', 1)
    completed = user.get('completed_tasks', [])
    
    today = datetime.now().date()
    available = []
    
    for task in TASKS_DATABASE:
        # Пропускаем выполненные
        if task['id'] in completed:
            continue
        
        # Проверяем уровень
        if task['required_level'] > level:
            continue
        
        # Проверяем дату разблокировки
        unlock_date = datetime.strptime(task['unlock_date'], '%Y-%m-%d').date()
        if today < unlock_date:
            continue
        
        # Для уровня 1-2: показываем задания по порядку
        if level < 3:
            # Проверяем что предыдущее задание выполнено
            prev_order = task['order'] - 1
            if prev_order > 0:
                prev_tasks = [t for t in TASKS_DATABASE if t['order'] == prev_order]
                if prev_tasks and prev_tasks[0]['id'] not in completed:
                    continue
        
        available.append(task)
    
    # Для уровня 1-2: только одно задание
    if level < 3 and available:
        available = [min(available, key=lambda x: x['order'])]
    
    return available


def get_task_by_id(task_id):
    """Получить задание по ID"""
    for task in TASKS_DATABASE:
        if task['id'] == task_id:
            return task
    return None


def complete_task(user_id, task_id):
    """Засчитать выполнение задания"""
    user = get_user(user_id)
    task = get_task_by_id(task_id)
    
    if not task:
        return None
    
    # Проверяем что задание ещё не выполнено
    completed = user.get('completed_tasks', [])
    if task_id in completed:
        return None
    
    # Добавляем задание в выполненные
    completed.append(task_id)
    
    # Начисляем XP
    current_xp = user.get('xp', 0)
    new_xp = current_xp + task['xp_reward']
    
    # Проверяем повышение уровня
    current_level = user.get('level', 1)
    new_level = min(10, (new_xp // 100) + 1)
    level_up = new_level > current_level
    
    # Обновляем пользователя
    update_user(user_id, {
        'xp': new_xp,
        'level': new_level,
        'completed_tasks': completed,
        'tasks_completed': len(completed)
    })
    
    return {
        'xp_gained': task['xp_reward'],
        'new_xp': new_xp,
        'level_up': level_up,
        'old_level': current_level,
        'new_level': new_level
    }


# ============================================
# ОБРАБОТЧИКИ
# ============================================

def handle_tasks_menu(bot, message):
    """Главное меню заданий"""
    user_id = message.from_user.id
    progress = get_user_progress(user_id)
    
    level_emoji = ["🌱", "🌿", "🌳", "🌲", "🎯", "⭐", "💎", "🏆", "👑", "🔥"]
    emoji = level_emoji[min(progress['level']-1, 9)]
    
    text = f"""
🎯 **ЗАДАНИЯ МЕДИАЦЕНТРА**

{emoji} **Твой прогресс:**
• Уровень: {progress['level']}/10
• XP: {progress['xp']} (до след.: {progress['xp_to_next']})
• Выполнено: {progress['completed_count']} заданий

💡 Выполняй задания, получай опыт и повышай уровень!
"""
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton(
            f"📋 Доступные задания ({progress['available_count']})",
            callback_data="tasks_available"
        ),
        telebot.types.InlineKeyboardButton(
            f"✅ Выполненные ({progress['completed_count']})",
            callback_data="tasks_completed"
        ),
        telebot.types.InlineKeyboardButton("📊 Мой прогресс", callback_data="tasks_progress"),
        telebot.types.InlineKeyboardButton("❓ Как работает система?", callback_data="tasks_help")
    )
    
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup,
        parse_mode='Markdown'
    )


def handle_available_tasks(bot, call):
    """Показать доступные задания"""
    user_id = call.from_user.id
    available = get_available_tasks(user_id)
    
    if not available:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
        
        bot.edit_message_text(
            "🎉 **Все доступные задания выполнены!**\n\nЖди новое задание или повышай уровень 🚀",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    text = "📋 **ДОСТУПНЫЕ ЗАДАНИЯ**\n\nВыбери задание:\n\n"
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for task in available:
        task_type = task.get('type', 'unknown')
        if task_type == "photo":
            emoji = "📸"
        elif task_type == "video":
            emoji = "🎥"
        elif task_type == "ai":
            emoji = "🤖"
        else:
            emoji = "📋"
        
        button_text = f"{emoji} {task['title']} (+{task['xp_reward']} XP)"
        markup.add(
            telebot.types.InlineKeyboardButton(
                button_text,
                callback_data=f"task_view_{task['id']}"
            )
        )
    
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def handle_task_view(bot, call):
    """Показать детали задания"""
    task_id = call.data.replace("task_view_", "")
    task = get_task_by_id(task_id)
    
    if not task:
        bot.answer_callback_query(call.id, "❌ Задание не найдено")
        return
    
    task_type = task.get('type', 'unknown')
    if task_type == "photo":
        emoji = "📸"
    elif task_type == "video":
        emoji = "🎥"
    elif task_type == "ai":
        emoji = "🤖"
    else:
        emoji = "📋"
    
    text = f"""{emoji} **{task['title']}**

{task['description']}

{task['instructions']}

⭐ **Награда:** +{task['xp_reward']} XP
"""
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "✅ Отправить выполнение",
            callback_data=f"task_submit_{task_id}"
        ),
        telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_available")
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


# Словарь для отслеживания ожидания отправки задания
waiting_for_task_submission = {}


def handle_task_submit(bot, call):
    """Начать процесс отправки задания"""
    task_id = call.data.replace("task_submit_", "")
    task = get_task_by_id(task_id)
    
    if not task:
        bot.answer_callback_query(call.id, "❌ Задание не найдено")
        return
    
    user_id = call.from_user.id
    waiting_for_task_submission[user_id] = task_id
    
    task_type = task.get('type', 'unknown')
    if task_type == "video":
        prompt = "🎥 Отправь видео выполнения задания"
    elif task_type == "ai":
        prompt = "🤖 Отправь скриншот или текст работы с AI"
    else:
        prompt = "📸 Отправь фото выполнения задания"
    
    bot.edit_message_text(
        f"{prompt}\n\n💡 Можешь добавить текстовое описание",
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id)


def handle_task_submission(bot, message):
    """Обработка отправленного задания"""
    user_id = message.from_user.id
    
    if user_id not in waiting_for_task_submission:
        return False
    
    task_id = waiting_for_task_submission[user_id]
    task = get_task_by_id(task_id)
    
    if not task:
        bot.send_message(message.chat.id, "❌ Ошибка: задание не найдено")
        del waiting_for_task_submission[user_id]
        return True
    
    # Получаем медиа
    file_id = None
    media_type = None
    caption = message.caption or message.text or ""
    
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.text:
        caption = message.text
        media_type = "text"
    
    # Подтверждение пользователю
    bot.send_message(
        message.chat.id,
        "✅ **Задание отправлено на проверку!**\n\nДмитрий Витальевич скоро проверит 👨‍🏫",
        parse_mode='Markdown'
    )
    
    # Отправляем админу (ID: 397724997)
    ADMIN_ID = 397724997
    
    user = get_user(user_id)
    user_name = user.get('first_name', 'Пользователь')
    user_nickname = user.get('nickname', '')
    display_name = f"{user_name} (@{user_nickname})" if user_nickname else user_name
    
    admin_text = f"""📬 **НОВОЕ ЗАДАНИЕ НА ПРОВЕРКУ**

👤 От: {display_name} (ID: {user_id})

🎯 Задание: {task['title']}
⭐ Награда: {task['xp_reward']} XP

💬 Комментарий ученика:
{caption if caption else '—'}
"""
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "✅ Принять",
            callback_data=f"approve_{user_id}_{task_id}"
        ),
        telebot.types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=f"reject_{user_id}_{task_id}"
        )
    )
    
    # Отправляем в зависимости от типа медиа
    if media_type == "photo":
        bot.send_photo(
            ADMIN_ID,
            file_id,
            caption=admin_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    elif media_type == "video":
        bot.send_video(
            ADMIN_ID,
            file_id,
            caption=admin_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # Убираем из ожидания
    del waiting_for_task_submission[user_id]
    
    return True


def handle_task_approve(bot, call):
    """Принять задание (админ)"""
    try:
        # Парсим callback_data: "approve_USER_ID_task_001"
        parts = call.data.split('_')
        user_id = int(parts[1])
        task_id = '_'.join(parts[2:])  # task_001, task_002 и т.д.
        
        print(f"✅ Одобрение: user_id={user_id}, task_id={task_id}")
        
    except Exception as e:
        print(f"❌ Ошибка парсинга: {call.data}, error: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка парсинга данных")
        return
Копировать

    
    task = get_task_by_id(task_id)
    if not task:
        bot.answer_callback_query(call.id, "❌ Задание не найдено")
        return
    
    # Засчитываем задание
    result = complete_task(user_id, task_id)
    
    if not result:
        bot.answer_callback_query(call.id, "❌ Задание уже выполнено")
        return
    
    # Уведомляем ученика
    reward_text = f"""✅ **ЗАДАНИЕ ЗАСЧИТАНО!**

🎯 Задание: {task['title']}
⭐ Получено: +{result['xp_gained']} XP
📊 Всего XP: {result['new_xp']}
"""
    
    if result['level_up']:
        level_emoji = ["🌱", "🌿", "🌳", "🌲", "🎯", "⭐", "💎", "🏆", "👑", "🔥"]
        emoji = level_emoji[min(result['new_level']-1, 9)]
        reward_text += f"\n\n🎉 **НОВЫЙ УРОВЕНЬ!** {emoji}\n{result['old_level']} → {result['new_level']}"
    
    reward_text += "\n\nТак держать! 🔥"
    
    bot.send_message(user_id, reward_text, parse_mode='Markdown')
    
    # Подтверждение админу
    bot.edit_message_text(
        call.message.text + "\n\n✅ **ПРИНЯТО**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id, "✅ Задание засчитано!")


def handle_task_reject(bot, call):
    """Отклонить задание (админ)"""
    parts = call.data.split('_')
    user_id = int(parts[1])
    task_id = parts[2]
    
    task = get_task_by_id(task_id)
    if not task:
        bot.answer_callback_query(call.id, "❌ Задание не найдено")
        return
    
    # Уведомляем ученика
    bot.send_message(
        user_id,
        f"❌ **Задание отклонено**\n\n🎯 {task['title']}\n\n"
        f"💬 Дмитрий Витальевич напишет тебе комментарий",
        parse_mode='Markdown'
    )
    
    # Подтверждение админу
    bot.edit_message_text(
        call.message.text + "\n\n❌ **ОТКЛОНЕНО**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id, "❌ Отклонено, напиши причину юзеру")


def handle_completed_tasks(bot, call):
    """Показать выполненные задания"""
    user_id = call.from_user.id
    user = get_user(user_id)
    completed = user.get('completed_tasks', [])
    
    if not completed:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
        
        bot.edit_message_text(
            "📭 **Пока нет выполненных заданий**\n\nНачни с первого задания!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    # Собираем выполненные задания
    completed_list = []
    total_xp = 0
    
    for task_id in completed:
        task = get_task_by_id(task_id)
        if task:
            task_type = task.get('type', 'unknown')
            if task_type == "photo":
                emoji = "📸"
            elif task_type == "video":
                emoji = "🎥"
            elif task_type == "ai":
                emoji = "🤖"
            else:
                emoji = "📋"
            
            completed_list.append(f"{emoji} {task['title']} (+{task['xp_reward']} XP)")
            total_xp += task['xp_reward']
    
    text = "✅ **ВЫПОЛНЕННЫЕ ЗАДАНИЯ**\n\n" + "\n".join(completed_list)
    text += f"\n\n💰 **Всего заработано:** {total_xp} XP"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def handle_tasks_progress(bot, call):
    """Показать прогресс"""
    user_id = call.from_user.id
    progress = get_user_progress(user_id)
    
    level_emoji = ["🌱", "🌿", "🌳", "🌲", "🎯", "⭐", "💎", "🏆", "👑", "🔥"]
    emoji = level_emoji[min(progress['level']-1, 9)]
    
    # Прогресс-бар
    bar_length = 10
    filled = int((progress['xp'] % 100) / 10)
    bar = "▓" * filled + "░" * (bar_length - filled)
    
    level_val = progress['level']
    xp_val = progress['xp']
    xp_next = progress['xp_to_next']
    completed_val = progress['completed_count']
    available_val = progress['available_count']
    
    text = f"""📊 **ТВОЙ ПРОГРЕСС**

{emoji} **Уровень:** {level_val}/10

⭐ **Опыт:** {xp_val} XP
{bar}
До след. уровня: {xp_next} XP

📋 **Задания:**
✅ Выполнено: {completed_val}
📝 Доступно: {available_val}

💡 Продолжай в том же духе!
"""
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def handle_tasks_help(bot, call):
    """Помощь по системе заданий"""
    text = """❓ **КАК РАБОТАЕТ СИСТЕМА ЗАДАНИЙ**

**🎯 УРОВНИ:**
• Начинаешь с 1 уровня
• Каждые 100 XP = новый уровень
• Максимум 10 уровней

**📋 ЗАДАНИЯ:**
• До 3 уровня (0-4 задания): задания открываются по порядку
• С 3 уровня (5+ заданий): можешь выбирать из доступных

**⭐ ОПЫТ (XP):**
• За каждое задание даётся XP
• AI-задания: 35-70 XP
• Фото-задания: 45-75 XP  
• Видео-задания: 70-150 XP

**✅ КАК ВЫПОЛНИТЬ:**
1. Выбери задание
2. Прочитай описание
3. Выполни задание
4. Отправь результат боту
5. Жди проверки от Дмитрия Витальевича

**🎁 НАГРАДЫ:**
• XP за каждое задание
• Новые уровни
• Доступ к новым заданиям
• Право выбора (с 3 уровня)

💡 Если непонятно - спроси у Дмитрия Витальевича!
"""
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)
