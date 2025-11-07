"""
Система заданий и прогресса
"""
import telebot
from database import get_user, update_user
from datetime import datetime, timedelta

# База заданий
TASKS_DATABASE = {
    # ============================================
    # НОВИЧОК (уровень 1-2) - БЕЗ ВЫБОРА
    # ============================================
    
    # НЕДЕЛЯ 1: 12-18 ноября
    "task_001": {
        "id": "task_001",
        "title": "📱 Первый портрет",
        "description": "Сфотографируй портрет мамы, папы или друга на телефон\n\n✨ **Что нужно:**\n• Правило третей (глаза на верхней линии)\n• Естественный свет (у окна)\n• Чистый фон\n• Модель смотрит в камеру или чуть в сторону",
        "type": "photo",
        "level_required": 1,
        "week": 1,
        "available_from": "2024-11-12",
        "xp_reward": 50,
        "instructions": "Загрузи фото и напиши: где снимал, какой свет использовал, как применил правило третей",
    },
    
    # НЕДЕЛЯ 2: 19-25 ноября
    "task_002": {
        "id": "task_002",
        "title": "💡 Свет решает всё",
        "description": "Сделай 3 селфи с разным освещением\n\n🔦 **Три варианта:**\n1. Естественный свет у окна (днём)\n2. Верхний свет (лампа на потолке)\n3. Боковой свет (настольная лампа сбоку)",
        "type": "photo",
        "level_required": 1,
        "week": 2,
        "available_from": "2024-11-19",
        "xp_reward": 45,
        "instructions": "Загрузи 3 фото и опиши как свет меняет картинку",
    },
    
    # НЕДЕЛЯ 3: 26 ноября - 2 декабря
    "task_003": {
        "id": "task_003",
        "title": "🤖 План съёмки концерта",
        "description": "Попроси AI-помощника составить план съёмки школьного концерта\n\n📝 **Что должно быть в плане:**\n• Какие кадры снимать (общие, средние, крупные)\n• Кого снимать (выступающие, зрители, организаторы)\n• Вопросы для интервью (3-5 вопросов)\n• Композиция кадров\n• Важные моменты",
        "type": "ai",
        "level_required": 1,
        "week": 3,
        "available_from": "2024-11-26",
        "xp_reward": 40,
        "instructions": "Напиши хороший промпт AI, получи план и отправь мне текстом или скриншотом",
        "ai_prompt_example": "Составь подробный план съёмки школьного концерта. Включи: список кадров с описанием композиции, кого и когда снимать, 5 вопросов для интервью с участниками"
    },
    
    # НЕДЕЛЯ 4: 3-9 декабря
    "task_004": {
        "id": "task_004",
        "title": "🤖 Идеи для контента",
        "description": "Попроси AI придумать 5 идей для видео про школьную жизнь\n\n💡 **Цель:**\n• Научиться правильно формулировать запросы AI\n• Получить креативные идеи\n• Выбрать самую интересную",
        "type": "ai",
        "level_required": 1,
        "week": 4,
        "available_from": "2024-12-03",
        "xp_reward": 35,
        "instructions": "Отправь список из 5 идей от AI и отметь какая тебе больше понравилась",
        "ai_prompt_example": "Придумай 5 креативных идей для коротких видео (30-60 сек) о школьной жизни. Для каждой идеи опиши: концепцию, что снимать, как подать материал"
    },
    
    # ============================================
    # НОВОГОДНИЙ ПРОЕКТ (3 недели)
    # ============================================
    
    # НЕДЕЛЯ 5: 10-16 декабря - ЭТАП 1
    "task_005": {
        "id": "task_005",
        "title": "🎄 НГ-проект: Сценарий (1/3)",
        "description": "**НОВОГОДНИЙ ПРОЕКТ - ЭТАП 1 из 3**\n\nПопроси AI написать сценарий новогоднего поздравления для друзей (15-30 сек)\n\n📝 **Что включить:**\n• Идея ролика\n• Что будет происходить\n• Текст/реплики\n• Настроение (весёлое, тёплое, креативное)",
        "type": "ai",
        "level_required": 1,
        "week": 5,
        "available_from": "2024-12-10",
        "xp_reward": 50,
        "instructions": "Отправь готовый сценарий текстом",
        "ai_prompt_example": "Напиши сценарий короткого новогоднего видео-поздравления для друзей (20-30 секунд). Креативное, весёлое, с изюминкой. Опиши: что происходит в кадре, текст поздравления, финальный кадр"
    },
    
    # НЕДЕЛЯ 6: 17-23 декабря - ЭТАП 2
    "task_006": {
        "id": "task_006",
        "title": "🎬 НГ-проект: Режиссура (2/3)",
        "description": "**НОВОГОДНИЙ ПРОЕКТ - ЭТАП 2 из 3**\n\nПопроси AI создать режиссёрский план съёмки твоего новогоднего ролика\n\n🎥 **Что должно быть:**\n• Покадровый план (какие планы: общий/средний/крупный)\n• Композиция каждого кадра\n• Свет и локация\n• Музыка (какое настроение)\n• Переходы между кадрами",
        "type": "ai",
        "level_required": 1,
        "week": 6,
        "available_from": "2024-12-17",
        "xp_reward": 60,
        "instructions": "Отправь режиссёрский план. Используй сценарий из предыдущего задания!",
        "ai_prompt_example": "На основе сценария [вставь свой сценарий] создай режиссёрский план съёмки. Распиши покадрово: номер кадра, план (общий/средний/крупный/деталь), композиция, что в кадре, длительность, освещение. Добавь рекомендации по музыке"
    },
    
    # НЕДЕЛЯ 7: 24-30 декабря - ЭТАП 3
    "task_007": {
        "id": "task_007",
        "title": "📹 НГ-проект: Съёмка (3/3)",
        "description": "**НОВОГОДНИЙ ПРОЕКТ - ФИНАЛ!**\n\nСними и смонтируй новогоднее поздравление!\n\n🎬 **Требования:**\n• По твоему режиссёрскому плану\n• Длительность: 15-30 секунд\n• Смонтируй в CapCut\n• Музыка (без АП!)\n• Новогоднее настроение\n\n💡 **Нужна помощь с монтажом?** Обратись к Дмитрию Витальевичу!",
        "type": "video",
        "level_required": 1,
        "week": 7,
        "available_from": "2024-12-24",
        "xp_reward": 100,
        "instructions": "Загрузи готовый ролик в бот. Это твой первый полноценный проект! 🎉",
    },
    
    # ============================================
    # ЛЮБИТЕЛЬ (уровень 3+) - ЕСТЬ ВЫБОР
    # ============================================
    
    # НЕДЕЛЯ 8: 31 декабря - 6 января (КАНИКУЛЫ)
    "task_008a": {
        "id": "task_008a",
        "title": "🎆 Новогодняя атмосфера",
        "description": "Сними серию из 5 фото новогодней атмосферы\n\n📸 **Темы:**\n• Ёлка/украшения\n• Огни и гирлянды\n• Праздничный стол\n• Семья/друзья\n• Зимний пейзаж\n\n✨ Используй правило третей и работай со светом!",
        "type": "photo",
        "level_required": 3,
        "week": 8,
        "available_from": "2024-12-31",
        "xp_reward": 60,
        "instructions": "Загрузи 5 лучших фото с описанием",
        "choice_group": 1  # Группа выбора
    },
    
    "task_008b": {
        "id": "task_008b",
        "title": "🎄 Новогодние истории",
        "description": "Попроси AI придумать 3 идеи новогодних сторис для Instagram\n\n📱 **Для каждой истории:**\n• Концепция\n• Что снимать\n• Текст/надписи\n• Музыка/настроение",
        "type": "ai",
        "level_required": 3,
        "week": 8,
        "available_from": "2024-12-31",
        "xp_reward": 50,
        "instructions": "Отправь 3 идеи от AI",
        "choice_group": 1,  # Та же группа - можно выбрать только одно
        "ai_prompt_example": "Придумай 3 креативные идеи новогодних сторис для Instagram. Для каждой опиши: что снимать, как оформить, текст, музыкальное сопровождение, хештеги"
    },
    
    # НЕДЕЛЯ 9: 7-13 января
    "task_009a": {
        "id": "task_009a",
        "title": "🎤 Первое интервью",
        "description": "Сними короткое интервью (30-60 секунд)\n\n🎬 **Требования:**\n• 1-2 вопроса + ответы\n• Горизонтальная ориентация\n• Правило третей (собеседник смотрит в сторону пустого пространства)\n• Чистый звук\n• Можешь не монтировать",
        "type": "video",
        "level_required": 3,
        "week": 9,
        "available_from": "2025-01-07",
        "xp_reward": 70,
        "instructions": "Загрузи видео. Напиши кого снимал и какие вопросы задавал",
        "choice_group": 2
    },
    
    "task_009b": {
        "id": "task_009b",
        "title": "🤖 Вопросы для интервью",
        "description": "Попроси AI составить 10 интересных вопросов для интервью с одноклассником о его увлечениях\n\n❓ **Типы вопросов:**\n• Открытые (не да/нет)\n• Про хобби и интересы\n• Про мечты и планы\n• Неожиданные/креативные",
        "type": "ai",
        "level_required": 3,
        "week": 9,
        "available_from": "2025-01-07",
        "xp_reward": 45,
        "instructions": "Отправь список вопросов",
        "choice_group": 2,
        "ai_prompt_example": "Составь 10 интересных открытых вопросов для интервью с одноклассником о его хобби и увлечениях. Вопросы должны быть нескучными, раскрывающими личность, с возможностью интересного рассказа"
    },
    
    # НЕДЕЛЯ 10: 14-20 января
    "task_010a": {
        "id": "task_010a",
        "title": "🌆 Золотой час",
        "description": "Сфоткай закат или рассвет\n\n📸 **Советы:**\n• За час до заката / после рассвета\n• Экспериментируй с силуэтами\n• Передний план + задний план\n• Правило третей (горизонт на 1/3)\n\n⏰ Закат зимой примерно в 16:30-17:00",
        "type": "photo",
        "level_required": 3,
        "week": 10,
        "available_from": "2025-01-14",
        "xp_reward": 65,
        "instructions": "Загрузи лучшее фото. Напиши время съёмки и настройки если помнишь",
        "choice_group": 3
    },
    
    "task_010b": {
        "id": "task_010b",
        "title": "🤖 Сценарий короткого видео",
        "description": "Напиши с AI сценарий видео про один день из жизни школьника (1 минута)\n\n📋 **Структура:**\n• Утро (подъём, сборы)\n• Школа (уроки, перемены)\n• После школы (друзья, хобби)\n• Вечер (дом, семья)\n• Закадровый текст",
        "type": "ai",
        "level_required": 3,
        "week": 10,
        "available_from": "2025-01-14",
        "xp_reward": 55,
        "instructions": "Отправь готовый сценарий с покадровым планом",
        "choice_group": 3,
        "ai_prompt_example": "Напиши сценарий 1-минутного видео 'Один день школьника'. Покадровый план: время суток, что происходит, план съёмки, длительность кадра. Добавь текст закадрового комментария на каждый блок"
    },
    
    # НЕДЕЛЯ 11: 21-27 января
    "task_011a": {
        "id": "task_011a",
        "title": "📸 Фото-серия: Школа",
        "description": "Сделай серию из 5 фото на тему 'Школьная жизнь'\n\n🎯 **Разные планы:**\n• Общий (класс, коридор)\n• Средний (группа людей)\n• Крупный (лицо, эмоции)\n• Деталь (руки, предметы)\n• Творческий (необычный ракурс)",
        "type": "photo",
        "level_required": 3,
        "week": 11,
        "available_from": "2025-01-21",
        "xp_reward": 75,
        "instructions": "Загрузи 5 фото. Подпиши каждое: какой план использовал",
        "choice_group": 4
    },
    
    "task_011b": {
        "id": "task_011b",
        "title": "🤖 Закадровый текст",
        "description": "Попроси AI написать закадровый текст для видео о школьном мероприятии\n\n📝 **Требования:**\n• 30-40 секунд чтения\n• Эмоциональный и живой язык\n• Вступление + основная часть + финал\n• Призыв к действию в конце",
        "type": "ai",
        "level_required": 3,
        "week": 11,
        "available_from": "2025-01-21",
        "xp_reward": 50,
        "instructions": "Отправь текст. Укажи для какого мероприятия (можешь придумать)",
        "choice_group": 4,
        "ai_prompt_example": "Напиши эмоциональный закадровый текст на 35 секунд для видео о школьном спортивном празднике. Структура: яркое начало, описание атмосферы и эмоций, финал с призывом. Язык простой, молодёжный"
    },
    
    # НЕДЕЛЯ 12: 28 января - 3 февраля
    "task_012a": {
        "id": "task_012a",
        "title": "🎬 Минутный ролик",
        "description": "Смонтируй видео длиной 45-60 секунд\n\n✂️ **Требования:**\n• Минимум 5 разных кадров\n• Музыка без АП\n• Плавные переходы\n• Тема: школа/друзья/хобби (выбери)\n• Монтаж в CapCut\n\n💡 Помощь нужна? → Дмитрий Витальевич",
        "type": "video",
        "level_required": 3,
        "week": 12,
        "available_from": "2025-01-28",
        "xp_reward": 90,
        "instructions": "Загрузи готовый ролик",
        "choice_group": 5
    },
    
    "task_012b": {
        "id": "task_012b",
        "title": "🤖 Контент-план на неделю",
        "description": "Попроси AI создать контент-план постов для соцсетей медиацентра на неделю\n\n📅 **Что включить:**\n• 5 постов\n• Тема каждого поста\n• Формат (фото/видео/карусель)\n• Текст (50-80 слов)\n• 5-7 хештегов",
        "type": "ai",
        "level_required": 3,
        "week": 12,
        "available_from": "2025-01-28",
        "xp_reward": 70,
        "instructions": "Отправь готовый контент-план",
        "choice_group": 5,
        "ai_prompt_example": "Создай контент-план на неделю для Instagram школьного медиацентра. 5 постов про жизнь медиацентра, съёмки, за кадром. Для каждого: день недели, тема, формат, текст поста 60 слов, 5 хештегов"
    },
}


def get_available_tasks(user_id):
    """Получить доступные задания для пользователя"""
    user = get_user(user_id)
    level = user.get('level', 1)
    completed = user.get('completed_tasks', [])
    completed_count = len(completed)
    
    today = datetime.now().date()
    available = []
    
    for task_id, task in TASKS_DATABASE.items():
        # Проверка уровня
        if task['level_required'] > level:
            continue
        
        # Проверка даты открытия
        available_from = datetime.strptime(task['available_from'], '%Y-%m-%d').date()
        if today < available_from:
            continue
        
        # Для уровня 1-2: только одно активное задание
        if completed_count < 5:  # До 3 уровня
            # Находим первое невыполненное задание по порядку
            sorted_tasks = sorted(
                [t for t in TASKS_DATABASE.values() if t['level_required'] == 1],
                key=lambda x: x['week']
            )
            
            for t in sorted_tasks:
                if t['id'] not in completed:
                    # Проверяем что дата подошла
                    t_available = datetime.strptime(t['available_from'], '%Y-%m-%d').date()
                    if today >= t_available and t['id'] == task_id:
                        available.append(task)
                    break
        
        # Для уровня 3+: показываем группы выбора
        else:
            if task['id'] not in completed:
                # Если задание с выбором - проверяем что другое из группы не выполнено
                if 'choice_group' in task:
                    group = task['choice_group']
                    group_completed = False
                    
                    for t_id, t in TASKS_DATABASE.items():
                        if t.get('choice_group') == group and t_id in completed:
                            group_completed = True
                            break
                    
                    if not group_completed:
                        available.append(task)
                else:
                    available.append(task)
    
    return available


def get_task_by_id(task_id):
    """Получить задание по ID"""
    return TASKS_DATABASE.get(task_id)


def is_task_completed(user_id, task_id):
    """Проверить выполнено ли задание"""
    user = get_user(user_id)
    completed = user.get('completed_tasks', [])
    return task_id in completed


def complete_task(user_id, task_id):
    """Отметить задание как выполненное"""
    user = get_user(user_id)
    
    task = get_task_by_id(task_id)
    if not task:
        return False
    
    if is_task_completed(user_id, task_id):
        return False
    
    completed = user.get('completed_tasks', [])
    completed.append(task_id)
    
    current_xp = user.get('xp', 0)
    new_xp = current_xp + task['xp_reward']
    
    current_level = user.get('level', 1)
    new_level = calculate_level(new_xp)
    
    update_user(user_id, {
        'completed_tasks': completed,
        'xp': new_xp,
        'level': new_level,
        'tasks_completed': len(completed)
    })
    
    return {
        'xp_gained': task['xp_reward'],
        'new_xp': new_xp,
        'level_up': new_level > current_level,
        'new_level': new_level
    }


def calculate_level(xp):
    """Рассчитать уровень по XP (каждые 100 XP = +1 уровень)"""
    level = min(10, (xp // 100) + 1)
    return level


def get_xp_for_next_level(current_xp):
    """Сколько XP до следующего уровня"""
    current_level = calculate_level(current_xp)
    if current_level >= 10:
        return 0
    
    next_level_xp = current_level * 100
    return next_level_xp - current_xp


def get_user_progress(user_id):
    """Получить прогресс пользователя"""
    user = get_user(user_id)
    
    xp = user.get('xp', 0)
    level = user.get('level', 1)
    completed = user.get('completed_tasks', [])
    
    available_tasks = get_available_tasks(user_id)
    
    return {
        'xp': xp,
        'level': level,
        'xp_to_next': get_xp_for_next_level(xp),
        'completed_count': len(completed),
        'available_count': len(available_tasks),
        'available_tasks': available_tasks
    }


def handle_tasks_menu(bot, message):
    """Главное меню заданий"""
    user_id = message.from_user.id
    progress = get_user_progress(user_id)
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    buttons = [
        telebot.types.InlineKeyboardButton("📋 Доступные задания", callback_data="tasks_available"),
        telebot.types.InlineKeyboardButton("✅ Выполненные", callback_data="tasks_completed"),
        telebot.types.InlineKeyboardButton("📊 Мой прогресс", callback_data="tasks_progress"),
        telebot.types.InlineKeyboardButton("❓ Как работает система?", callback_data="tasks_help"),
    ]
    
    markup.add(*buttons)
    
    level_emoji = ["🌱", "🌿", "🌳", "🌲", "🎯", "⭐", "💎", "🏆", "👑", "🔥"]
    emoji = level_emoji[min(progress['level']-1, 9)]
    
    # Специальное сообщение для уровня 3+
    choice_msg = ""
    if progress['level'] >= 3:
        choice_msg = "\n\n🎯 **У тебя 3 уровень!** Теперь можешь выбирать задания!"
    
    text = f"""
🎯 **ЗАДАНИЯ МЕДИАЦЕНТРА**

{emoji} **Твой прогресс:**
• Уровень: {progress['level']}/10
• XP: {progress['xp']} (до след.: {progress['xp_to_next']})
• Выполнено: {progress['completed_count']} заданий{choice_msg}

💡 Выполняй задания, получай опыт и повышай уровень!
"""
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

def handle_available_tasks(bot, call):
    """Показать доступные задания"""
    user_id = call.from_user.id
    progress = get_user_progress(user_id)
    available = progress['available_tasks']
    
    if not available:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
        
        bot.edit_message_text(
            "🎉 **Все доступные задания выполнены!**\n\nЖди новое задание или повышай уровень!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    # Группируем задания по choice_group если есть
    if progress['level'] >= 3:
        groups = {}
        for task in available:
            group = task.get('choice_group', 0)
            if group not in groups:
                groups[group] = []
            groups[group].append(task)
        
        # Показываем задания
        for group_id in sorted(groups.keys()):
            tasks = groups[group_id]
            
            if len(tasks) > 1:
                # Группа выбора
                for task in tasks:
                    emoji = {"photo": "📸", "video": "🎥", "ai": "🤖"}.get(task['type'], "📋")
                    markup.add(telebot.types.InlineKeyboardButton(
                        f"{emoji} {task['title']} (+{task['xp_reward']} XP)",
                        callback_data=f"task_view_{task['id']}"
                    ))
                markup.add(telebot.types.InlineKeyboardButton("⬇️ Выбери одно из заданий выше ⬇️", callback_data="dummy"))
            else:
                # Одиночное задание
                task = tasks[0]
                emoji = {"photo": "📸", "video": "🎥", "ai": "🤖"}.get(task['type'], "📋")
                markup.add(telebot.types.InlineKeyboardButton(
                    f"{emoji} {task['title']} (+{task['xp_reward']} XP)",
                    callback_data=f"task_view_{task['id']}"
                ))
    else:
        # Для уровня 1-2: одно задание
        for task in available:
            emoji = {"photo": "📸", "video": "🎥", "ai": "🤖"}.get(task['type'], "📋")
            markup.add(telebot.types.InlineKeyboardButton(
                f"{emoji} {task['title']} (+{task['xp_reward']} XP)",
                callback_data=f"task_view_{task['id']}"
            ))
    
    markup.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="tasks_menu"))
    
    choice_text = ""
    if progress['level'] >= 3:
        choice_text = "\n\n💡 Можешь выбрать любое задание из доступных!"
    
    text = f"""
📋 **ДОСТУПНЫЕ ЗАДАНИЯ**

У тебя {len(available)} доступных заданий{choice_text}
"""
    
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
    
    user_id = call.from_user.id
    
    # Эмодзи типа
    emoji = {"photo": "📸", "video": "🎥", "ai": "🤖"}.get(task['type'], "📋")
    
    # Формируем текст
    text = f"""
{emoji} **{task['title']}**

{task['description']}

---

📝 **Как выполнить:**
{task['instructions']}

⭐ **Награда:** +{task['xp_reward']} XP
"""
    
    # Добавляем пример промпта для AI-заданий
    if task['type'] == 'ai' and 'ai_prompt_example' in task:
        text += f"\n\n💡 **Пример промпта:**\n`{task['ai_prompt_example']}`"
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("✅ Отправить выполнение", callback_data=f"task_submit_{task_id}"),
        telebot.types.InlineKeyboardButton("◀️ Назад к заданиям", callback_data="tasks_available")
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def handle_task_submit(bot, call):
    """Подготовка к отправке выполнения"""
    task_id = call.data.replace("task_submit_", "")
    task = get_task_by_id(task_id)
    
    if not task:
        bot.answer_callback_query(call.id, "❌ Задание не найдено")
        return
    
    user_id = call.from_user.id
    
    # Сохраняем что пользователь отправляет задание
    if user_id not in waiting_for_task_submission:
        waiting_for_task_submission[user_id] = {}
    waiting_for_task_submission[user_id] = task_id
    
    emoji = {"photo": "📸", "video": "🎥", "ai": "🤖"}.get(task['type'], "📋")
    
    if task['type'] == 'photo':
        instruction = "📸 **Отправь фото** (или несколько) в следующем сообщении"
    elif task['type'] == 'video':
        instruction = "🎥 **Отправь видео** в следующем сообщении"
    else:  # ai
        instruction = "📝 **Отправь текст** (результат работы с AI) в следующем сообщении"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("❌ Отмена", callback_data="tasks_available"))
    
    text = f"""
{emoji} **{task['title']}**

{instruction}

💡 После отправки задание отправится на проверку Дмитрию Витальевичу
"""
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


# Хранилище ожиданий отправки
waiting_for_task_submission = {}


def handle_task_submission(bot, message):
    """Обработка отправленного задания"""
    user_id = message.from_user.id
    
    # Проверяем что пользователь в режиме отправки
    if user_id not in waiting_for_task_submission:
        return False
    
    task_id = waiting_for_task_submission[user_id]
    task = get_task_by_id(task_id)
    
    if not task:
        del waiting_for_task_submission[user_id]
        return False
    
    user = get_user(user_id)
    username = user.get('username', 'Без имени')
    
    # Получаем ID админа (Дмитрий Витальевич)
    # ЗАМЕНИ на свой Telegram ID!
    ADMIN_ID = 123456789  # ← ТВОЙ TELEGRAM ID
    
    # Формируем сообщение админу
    admin_text = f"""
📥 **НОВОЕ ВЫПОЛНЕНИЕ ЗАДАНИЯ**

👤 **От:** {username} (ID: {user_id})
🎯 **Задание:** {task['title']}
⭐ **Награда:** {task['xp_reward']} XP

📝 **Тип:** {{"photo": "Фото", "video": "Видео", "ai": "AI-работа"}.get(task['type'])}
"""
    
    # Пересылаем контент админу
    try:
        if message.content_type == 'photo':
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_text, parse_mode='Markdown')
        elif message.content_type == 'video':
            bot.send_video(ADMIN_ID, message.video.file_id, caption=admin_text, parse_mode='Markdown')
        elif message.content_type == 'text':
            bot.send_message(ADMIN_ID, admin_text + f"\n\n💬 **Текст:**\n{message.text}", parse_mode='Markdown')
        
        # Кнопки одобрения/отклонения
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            telebot.types.InlineKeyboardButton("✅ Принять", callback_data=f"approve_{user_id}_{task_id}"),
            telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}_{task_id}")
        )
        bot.send_message(ADMIN_ID, "⬆️ Проверь выполнение:", reply_markup=markup)
        
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
    
    # Убираем из режима ожидания
    del waiting_for_task_submission[user_id]
    
    # Подтверждение пользователю
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎯 Мои задания", callback_data="tasks_menu"))
    
    bot.send_message(
        message.chat.id,
        f"✅ **Задание отправлено на проверку!**\n\n🎯 Задание: {task['title']}\n⏳ Жди результата от Дмитрия Витальевича",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    return True


def handle_task_approve(bot, call):
    """Админ одобряет задание"""
    parts = call.data.split("_")
    user_id = int(parts[1])
    task_id = parts[2]
    
    # Засчитываем задание
    result = complete_task(user_id, task_id)
    
    if not result:
        bot.answer_callback_query(call.id, "❌ Ошибка")
        return
    
    task = get_task_by_id(task_id)
    
    # Уведомляем пользователя
    level_up_text = ""
    if result['level_up']:
        level_up_text = f"\n\n🎉 **УРОВЕНЬ ПОВЫШЕН!** Теперь ты {result['new_level']} уровня!"
        
        # Особое сообщение при достижении 3 уровня
        if result['new_level'] == 3:
            level_up_text += "\n\n🎯 **Теперь ты можешь выбирать задания!**"
    
    user_text = f"""
✅ **ЗАДАНИЕ ЗАСЧИТАНО!**

🎯 Задание: {task['title']}
⭐ Получено: +{result['xp_gained']} XP
📊 Всего XP: {result['new_xp']}{level_up_text}

Так держать! 🔥
"""
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📋 Следующее задание", callback_data="tasks_available"))
    
    bot.send_message(user_id, user_text, reply_markup=markup, parse_mode='Markdown')
    
    # Подтверждение админу
    bot.edit_message_text(
        call.message.text + "\n\n✅ **ПРИНЯТО**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id, "✅ Задание засчитано!")


def handle_task_reject(bot, call):
    """Админ отклоняет задание"""
    parts = call.data.split("_")
    user_id = int(parts[1])
    task_id = parts[2]
    
    task = get_task_by_id(task_id)
    
    # Уведомляем пользователя
    user_text = f"""
❌ **Задание не принято**

🎯 Задание: {task['title']}

💬 Дмитрий Витальевич оставит комментарий. Исправь и отправь снова!
"""
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔄 К заданию", callback_data=f"task_view_{task_id}"))
    
    bot.send_message(user_id, user_text, reply_markup=markup, parse_mode='Markdown')
    
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
            emoji = {"photo": "📸", "video": "🎥", "ai": "🤖"}.get(task['type'], "📋")
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
    
    text = f"""
📊 **ТВОЙ ПРОГРЕСС**

{emoji} **Уровень:** {progress['level']}/10

⭐ **Опыт:** {progress['xp']} XP
{bar}
До след. уровня: {progress['xp_to_next']} XP

📋 **Задания:**
✅ Выполнено: {progress['completed_count']}
📝 Доступно: {progress['available_count']}

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
    text = """
❓ **КАК РАБОТАЕТ СИСТЕМА ЗАДАНИЙ**

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
