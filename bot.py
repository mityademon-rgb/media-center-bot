import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os
from openai import OpenAI
import sqlite3
from datetime import datetime, timedelta
import random
import json

# Токен и OpenAI клиент
bot = telebot.TeleBot(os.environ['TELEGRAM_TOKEN'])
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# Админ ID
ADMIN_ID = 397724997

# Подключение к SQLite
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, name TEXT, experience TEXT, interests TEXT)''')
conn.commit()

# ============== БАЗОВЫЕ ФУНКЦИИ БД ==============
def sql(q, args=(), many=False):
    c = conn.cursor()
    c.execute(q, args)
    conn.commit()
    return c.fetchall() if many else c.fetchone()

def init_weekly_db():
    sql("""CREATE TABLE IF NOT EXISTS weekly_meta(
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    sql("""CREATE TABLE IF NOT EXISTS weekly_tasks(
        week_id TEXT PRIMARY KEY,
        kind TEXT,
        title TEXT,
        description TEXT,
        media_url TEXT,
        deadline TEXT,
        quiz_q TEXT,
        quiz_a TEXT,
        quiz_b TEXT,
        quiz_c TEXT,
        quiz_correct INTEGER
    )""")
    sql("""CREATE TABLE IF NOT EXISTS weekly_points(
        user_id INTEGER,
        week_id TEXT,
        points INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, week_id)
    )""")
    sql("""CREATE TABLE IF NOT EXISTS weekly_submissions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        week_id TEXT,
        file_id TEXT,
        file_type TEXT,
        caption TEXT,
        ts TEXT
    )""")
    sql("""CREATE TABLE IF NOT EXISTS weekly_awards(
        user_id INTEGER,
        week_id TEXT,
        type TEXT,
        PRIMARY KEY(user_id, week_id, type)
    )""")
    sql("""CREATE TABLE IF NOT EXISTS weekly_test_states(
        user_id INTEGER,
        week_id TEXT,
        q_index INTEGER DEFAULT 0,
        score INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, week_id)
    )""")
    
    # ===== НОВЫЕ ТАБЛИЦЫ ДЛЯ ГЕЙМИФИКАЦИИ =====
    sql("""CREATE TABLE IF NOT EXISTS user_stats(
        user_id INTEGER PRIMARY KEY,
        total_points INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        streak_days INTEGER DEFAULT 0,
        last_visit TEXT,
        achievements TEXT DEFAULT '',
        guild_id INTEGER DEFAULT NULL,
        energy INTEGER DEFAULT 100,
        last_spin TEXT,
        quests_completed INTEGER DEFAULT 0,
        ai_questions INTEGER DEFAULT 0,
        videos_submitted INTEGER DEFAULT 0
    )""")
    
    sql("""CREATE TABLE IF NOT EXISTS daily_rewards(
        user_id INTEGER,
        date TEXT,
        claimed INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, date)
    )""")
    
    sql("""CREATE TABLE IF NOT EXISTS quests(
        quest_id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        tasks TEXT,
        reward_points INTEGER,
        reward_achievement TEXT
    )""")
    
    sql("""CREATE TABLE IF NOT EXISTS user_quests(
        user_id INTEGER,
        quest_id TEXT,
        progress TEXT DEFAULT '{}',
        completed INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, quest_id)
    )""")
    
    sql("""CREATE TABLE IF NOT EXISTS chests(
        user_id INTEGER,
        chest_type TEXT,
        opened INTEGER DEFAULT 0,
        date TEXT,
        PRIMARY KEY(user_id, date, chest_type)
    )""")
    
    sql("""CREATE TABLE IF NOT EXISTS guilds(
        guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        leader_id INTEGER,
        total_points INTEGER DEFAULT 0,
        members_count INTEGER DEFAULT 1
    )""")
    
    sql("""CREATE TABLE IF NOT EXISTS duels(
        duel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_id INTEGER,
        player2_id INTEGER,
        status TEXT,
        winner_id INTEGER,
        created_at TEXT
    )""")

def get_current_week():
    row = sql("SELECT value FROM weekly_meta WHERE key='current_week'")
    return row[0] if row else None

def set_current_week(week_id: str):
    if get_current_week() is None:
        sql("INSERT INTO weekly_meta(key,value) VALUES('current_week',?)", (week_id,))
    else:
        sql("UPDATE weekly_meta SET value=? WHERE key='current_week'", (week_id,))

def upsert_task(week_id, kind, title, description, media_url, deadline):
    row = sql("SELECT week_id FROM weekly_tasks WHERE week_id=?", (week_id,))
    if row:
        sql("""UPDATE weekly_tasks SET kind=?,title=?,description=?,media_url=?,deadline=? WHERE week_id=?""",
            (kind, title, description, media_url, deadline, week_id))
    else:
        sql("""INSERT INTO weekly_tasks(week_id,kind,title,description,media_url,deadline)
               VALUES(?,?,?,?,?,?)""", (week_id, kind, title, description, media_url, deadline))

def set_kind(kind):
    wid = get_current_week()
    if not wid: return False
    sql("UPDATE weekly_tasks SET kind=? WHERE week_id=?", (kind, wid))
    return True

def set_quiz(q, a, b, c, correct_idx):
    wid = get_current_week()
    if not wid: return False
    sql("""UPDATE weekly_tasks SET quiz_q=?,quiz_a=?,quiz_b=?,quiz_c=?,quiz_correct=?
           WHERE week_id=?""", (q, a, b, c, correct_idx, wid))
    return True

def get_task(week_id):
    return sql("""SELECT week_id,kind,title,description,media_url,deadline,
                         quiz_q,quiz_a,quiz_b,quiz_c,quiz_correct
                  FROM weekly_tasks WHERE week_id=?""", (week_id,))

def add_points(user_id, week_id, pts):
    row = sql("SELECT points FROM weekly_points WHERE user_id=? AND week_id=?", (user_id, week_id))
    if row:
        sql("UPDATE weekly_points SET points=points+? WHERE user_id=? AND week_id=?", (pts, user_id, week_id))
    else:
        sql("INSERT INTO weekly_points(user_id,week_id,points) VALUES(?,?,?)", (user_id, week_id, pts))
    
    update_user_stats(user_id, pts)

def get_points(user_id, week_id):
    row = sql("SELECT points FROM weekly_points WHERE user_id=? AND week_id=?", (user_id, week_id))
    return row[0] if row else 0

def already_awarded(user_id, week_id, award_type):
    return sql("SELECT 1 FROM weekly_awards WHERE user_id=? AND week_id=? AND type=?",
               (user_id, week_id, award_type)) is not None

def mark_awarded(user_id, week_id, award_type):
    sql("INSERT OR IGNORE INTO weekly_awards(user_id,week_id,type) VALUES(?,?,?)", (user_id, week_id, award_type))

def top_week(week_id, limit=10):
    return sql("""SELECT user_id, points FROM weekly_points
                  WHERE week_id=?
                  ORDER BY points DESC, user_id ASC
                  LIMIT ?""", (week_id, limit), many=True)

def format_task_text(row):
    _, kind, title, descr, media, deadline, qq, qa, qb, qc, cor = row
    t = [f"📅 Задание недели ({kind or 'не задано'})\n\n🧩 {title or '—'}\n\n{descr or '—'}"]
    if media: t.append(f"🔗 Материалы: {media}")
    if deadline: t.append(f"⏳ Дедлайн: {deadline}")
    if kind == 'media':
        t.append("\nОтправь фото/видео с подписью #challenge — зачтём участие (+5 очков за первое).")
    if kind == 'quiz' and qq:
        t.append("\n🧠 Квиз доступен командой /quiz")
    if kind == 'minitest':
        t.append("\n📝 Мини-тест доступен командой /minitest")
    return "\n".join(t)

POINTS_MEDIA_FIRST = 5
POINTS_QUIZ_RIGHT = 3
POINTS_MINITEST = {3:5, 2:3, 1:1, 0:0}

MINITEST_QUESTIONS = [
    ("Что такое 'правило третей'?",
     ["A: Ставим объект на пересечениях сетки 3x3", "B: Снимаем три дубля", "C: Всегда центр"], 'A'),
    ("Какой свет делает лицо 'страшным'?",
     ["A: Сбоку", "B: Сверху", "C: Снизу"], 'C'),
    ("Что лучше — зумить или подойти ближе?",
     ["A: Зумить", "B: Подойти ближе", "C: Не важно"], 'B'),
]

def users_all_ids():
    cursor.execute("SELECT user_id FROM users")
    return [r[0] for r in cursor.fetchall()]

init_weekly_db()

# ============== СИСТЕМА УРОВНЕЙ И АЧИВОК ==============

LEVELS = [
    (0, "🌱 Новичок", "Ты только начинаешь свой путь!"),
    (50, "🎬 Оператор-стажёр", "Уже можешь снимать простые ролики!"),
    (150, "📹 Оператор", "Твои видео становятся лучше!"),
    (300, "🎥 Режиссёр", "Ты понимаешь язык кино!"),
    (500, "🏆 Мастер медиа", "Твои работы вдохновляют других!"),
    (800, "⭐ Легенда", "Ты звезда медиацентра!"),
    (1200, "👑 Гуру медиа", "Ты достиг вершины мастерства!"),
    (2000, "💎 Титан контента", "Легендарный уровень!")
]

ACHIEVEMENTS = {
    'first_test': ('🎓 Первый тест', 'Прошёл первый тест'),
    'first_challenge': ('📸 Первый челлендж', 'Отправил работу в #challenge'),
    'streak_3': ('🔥 Тройной стрик', 'Заходил 3 дня подряд'),
    'streak_7': ('⚡ Недельный стрик', 'Заходил 7 дней подряд'),
    'streak_30': ('💎 Месячный стрик', 'Заходил 30 дней подряд'),
    'quiz_master': ('🧠 Квиз-мастер', 'Правильно ответил на 5 квизов'),
    'top_3': ('🥉 Топ-3', 'Попал в топ-3 недели'),
    'content_creator': ('🎨 Креатор', 'Создал 10 работ'),
    'social_butterfly': ('🦋 Амбассадор', 'Пригласил 3 друзей'),
    'ai_master': ('🤖 ИИ-гуру', 'Задал 20 вопросов ИИ'),
    'quest_hero': ('⚔️ Герой квестов', 'Выполнил 5 квестов'),
    'lucky_one': ('🍀 Везунчик', 'Выиграл джекпот на колесе'),
    'duel_champion': ('👊 Чемпион дуэлей', 'Выиграл 5 дуэлей'),
    'chest_hunter': ('📦 Охотник за сокровищами', 'Открыл 10 сундуков'),
    'guild_master': ('🏰 Мастер гильдии', 'Создал или возглавил гильдию'),
    'level_10': ('🌟 Десятый уровень', 'Достиг уровня 10'),
    'perfectionist': ('💯 Перфекционист', 'Набрал 5/5 в тесте'),
    'night_owl': ('🦉 Ночная сова', 'Заходил после полуночи'),
    'early_bird': ('🐦 Ранняя пташка', 'Заходил до 6 утра'),
    'speed_demon': ('⚡ Быстрый как молния', 'Прошёл тест меньше чем за минуту')
}

# ============== КВЕСТЫ ==============

QUESTS = {
    'operator_path': {
        'title': '🎬 Путь оператора',
        'description': 'Освой базовые навыки оператора',
        'tasks': [
            {'type': 'test', 'target': 'video', 'desc': 'Пройди тест по видеосъёмке'},
            {'type': 'challenge', 'count': 3, 'desc': 'Отправь 3 работы в #challenge'},
            {'type': 'checklist', 'target': 'check_shooting', 'desc': 'Изучи чек-лист съёмки'}
        ],
        'reward_points': 50,
        'reward_achievement': 'content_creator'
    },
    'journalist_path': {
        'title': '📰 Путь журналиста',
        'description': 'Стань мастером слова',
        'tasks': [
            {'type': 'test', 'target': 'journalism', 'desc': 'Пройди тест по журналистике'},
            {'type': 'ai_text', 'count': 3, 'desc': 'Создай 3 текста с помощью ИИ'},
            {'type': 'checklist', 'target': 'check_interview', 'desc': 'Изучи вопросы для интервью'}
        ],
        'reward_points': 50,
        'reward_achievement': 'ai_master'
    },
    'master_challenge': {
        'title': '🏆 Вызов мастера',
        'description': 'Докажи, что ты лучший',
        'tasks': [
            {'type': 'streak', 'count': 7, 'desc': 'Заходи 7 дней подряд'},
            {'type': 'points', 'count': 100, 'desc': 'Набери 100 очков'},
            {'type': 'top', 'position': 3, 'desc': 'Попади в топ-3'}
        ],
        'reward_points': 100,
        'reward_achievement': 'quest_hero'
    }
}

def init_quests():
    for qid, qdata in QUESTS.items():
        row = sql("SELECT quest_id FROM quests WHERE quest_id=?", (qid,))
        if not row:
            sql("""INSERT INTO quests(quest_id, title, description, tasks, reward_points, reward_achievement)
                   VALUES(?,?,?,?,?,?)""", 
                (qid, qdata['title'], qdata['description'], json.dumps(qdata['tasks']), 
                 qdata['reward_points'], qdata.get('reward_achievement', '')))

def start_quest(user_id, quest_id):
    row = sql("SELECT completed FROM user_quests WHERE user_id=? AND quest_id=?", (user_id, quest_id))
    if row and row[0] == 1:
        return False, "Ты уже выполнил этот квест!"
    if not row:
        sql("INSERT INTO user_quests(user_id, quest_id) VALUES(?,?)", (user_id, quest_id))
    return True, "Квест начат! Удачи! 🎯"

def update_quest_progress(user_id, task_type, target=None):
    quests = sql("SELECT quest_id, progress FROM user_quests WHERE user_id=? AND completed=0", (user_id,), many=True)
    
    for quest_id, progress_str in quests:
        progress = json.loads(progress_str) if progress_str else {}
        quest_data = QUESTS.get(quest_id)
        if not quest_data:
            continue
        
        tasks = quest_data['tasks']
        all_done = True
        
        for i, task in enumerate(tasks):
            task_key = f"task_{i}"
            if task_key in progress and progress[task_key]:
                continue
            
            if task['type'] == task_type:
                if task_type == 'test' and task.get('target') == target:
                    progress[task_key] = True
                elif task_type == 'challenge':
                    count = progress.get(task_key + '_count', 0) + 1
                    progress[task_key + '_count'] = count
                    if count >= task.get('count', 1):
                        progress[task_key] = True
                elif task_type == 'checklist' and task.get('target') == target:
                    progress[task_key] = True
                elif task_type in ['streak', 'points', 'ai_text']:
                    # Проверяем условия
                    if task_type == 'streak':
                        row = sql("SELECT streak_days FROM user_stats WHERE user_id=?", (user_id,))
                        if row and row[0] >= task.get('count', 0):
                            progress[task_key] = True
                    # Добавь другие проверки...
            
            if task_key not in progress or not progress[task_key]:
                all_done = False
        
        sql("UPDATE user_quests SET progress=? WHERE user_id=? AND quest_id=?", 
            (json.dumps(progress), user_id, quest_id))
        
        if all_done:
            complete_quest(user_id, quest_id, quest_data)

def complete_quest(user_id, quest_id, quest_data):
    sql("UPDATE user_quests SET completed=1 WHERE user_id=? AND quest_id=?", (user_id, quest_id))
    pts = quest_data['reward_points']
    update_user_stats(user_id, pts)
    
    achievement = quest_data.get('reward_achievement')
    if achievement:
        unlock_achievement(user_id, achievement)
    
    try:
        bot.send_message(user_id, 
            f"🎉 КВЕСТ ЗАВЕРШЁН!\n\n"
            f"✨ {quest_data['title']}\n"
            f"🎁 +{pts} очков\n\n"
            f"Смотри новые квесты: /quests")
    except:
        pass

init_quests()

# ============== ЭНЕРГИЯ И АКТИВНОСТИ ==============

def use_energy(user_id, amount=10):
    row = sql("SELECT energy FROM user_stats WHERE user_id=?", (user_id,))
    if row:
        energy = row[0]
        if energy >= amount:
            sql("UPDATE user_stats SET energy=energy-? WHERE user_id=?", (amount, user_id))
            return True, energy - amount
        else:
            return False, energy
    return False, 0

def restore_energy(user_id):
    # Восстановление 1 энергии каждые 10 минут (можно настроить)
    sql("UPDATE user_stats SET energy=CASE WHEN energy<100 THEN 100 ELSE energy END WHERE user_id=?", (user_id,))

# ============== КОЛЕСО УДАЧИ ==============

WHEEL_PRIZES = [
    ('💰 10 очков', 10, 'points', 30),
    ('💰 20 очков', 20, 'points', 20),
    ('💰 50 очков', 50, 'points', 10),
    ('🎁 Бронзовый сундук', 'bronze', 'chest', 15),
    ('🎁 Серебряный сундук', 'silver', 'chest', 8),
    ('🎁 Золотой сундук', 'gold', 'chest', 3),
    ('⚡ +10 энергии', 10, 'energy', 10),
    ('🔥 x2 очки (1 час)', '2x_1h', 'boost', 2),
    ('🎯 Случайный квест', 'random', 'quest', 2)
]

def spin_wheel(user_id):
    today = datetime.now().date().isoformat()
    row = sql("SELECT last_spin FROM user_stats WHERE user_id=?", (user_id,))
    
    if row and row[0] == today:
        return False, "Ты уже крутил колесо сегодня! Приходи завтра! 🎰"
    
    # Крутим!
    prizes_list = []
    for prize in WHEEL_PRIZES:
        prizes_list.extend([prize] * prize[3])  # Добавляем по весу
    
    won = random.choice(prizes_list)
    name, value, prize_type, _ = won
    
    sql("UPDATE user_stats SET last_spin=? WHERE user_id=?", (today, user_id))
    
    # Выдаём награду
    if prize_type == 'points':
        update_user_stats(user_id, value)
        result = f"🎉 Ты выиграл {value} очков!"
    elif prize_type == 'chest':
        sql("INSERT OR IGNORE INTO chests(user_id, chest_type, date) VALUES(?,?,?)", 
            (user_id, value, today))
        result = f"🎁 Ты получил {name}! Открой: /chests"
    elif prize_type == 'energy':
        sql("UPDATE user_stats SET energy=CASE WHEN energy+?<=100 THEN energy+? ELSE 100 END WHERE user_id=?", 
            (value, value, user_id))
        result = f"⚡ Восстановлено {value} энергии!"
    else:
        result = f"✨ Ты получил: {name}!"
    
    if value == 50:  # Джекпот
        unlock_achievement(user_id, 'lucky_one')
    
    return True, result

# ============== СУНДУКИ ==============

CHEST_REWARDS = {
    'bronze': {'points': (5, 15), 'energy': (5, 10)},
    'silver': {'points': (15, 30), 'energy': (10, 20)},
    'gold': {'points': (30, 100), 'energy': (20, 50), 'achievement_chance': 0.3}
}

def open_chest(user_id, chest_type):
    row = sql("SELECT opened FROM chests WHERE user_id=? AND chest_type=? AND opened=0 LIMIT 1", 
              (user_id, chest_type))
    
    if not row:
        return False, f"У тебя нет {chest_type} сундука!"
    
    rewards = CHEST_REWARDS.get(chest_type, {})
    points = random.randint(*rewards.get('points', (5, 10)))
    energy = random.randint(*rewards.get('energy', (0, 5)))
    
    update_user_stats(user_id, points)
    sql("UPDATE user_stats SET energy=CASE WHEN energy+?<=100 THEN energy+? ELSE 100 END WHERE user_id=?", 
        (energy, energy, user_id))
    
    sql("UPDATE chests SET opened=1 WHERE user_id=? AND chest_type=? AND opened=0", 
        (user_id, chest_type))
    
    result = f"🎁 Открыт {chest_type} сундук!\n\n💰 +{points} очков\n⚡ +{energy} энергии"
    
    # Шанс на ачивку в золотом сундуке
    if chest_type == 'gold' and random.random() < rewards.get('achievement_chance', 0):
        result += "\n\n🏆 БОНУС: Случайная ачивка!"
        unlock_achievement(user_id, random.choice(list(ACHIEVEMENTS.keys())))
    
    # Проверяем ачивку охотника
    opened_count = sql("SELECT COUNT(*) FROM chests WHERE user_id=? AND opened=1", (user_id,))
    if opened_count and opened_count[0] >= 10:
        unlock_achievement(user_id, 'chest_hunter')
    
    return True, result

# ============== ГЕНЕРАТОР ИДЕЙ ОТ ИИ ==============

def generate_video_idea(user_id, theme=None):
    prompt = f"""Ты креативный директор медиацентра. Придумай ОДНУ крутую идею для короткого видео (до 1 минуты) для школьника.

Тема: {theme if theme else 'любая'}

Формат ответа:
📹 Название: [цепляющее название]
🎬 Концепция: [краткое описание на 2-3 предложения]
📝 Что снимать: [3-4 конкретных кадра]
💡 Совет: [один профессиональный совет]
⏱️ Хронометраж: [30-60 сек]

Делай идею простой, но WOW! Пиши по-молодёжному, с огоньком! 🔥"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты креативный генератор идей для подростков. Пиши ярко, энергично, с эмоджи!"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9
        )
        
        idea = response.choices[0].message.content
        
        # Начисляем очки за использование генератора
        update_user_stats(user_id, 2)
        
        return idea
    except Exception as e:
        return f"Ошибка генерации: {e}"

def generate_prediction(user_id):
    user_row = sql("SELECT name, total_points, level FROM user_stats JOIN users ON user_stats.user_id=users.user_id WHERE user_stats.user_id=?", (user_id,))
    
    name = user_row[0] if user_row else "Креатор"
    points = user_row[1] if user_row else 0
    level = user_row[2] if user_row else 1
    
    prompt = f"""Ты мудрый наставник медиацентра с магическим даром предсказания. 
    
Ученик: {name}
Текущий уровень: {level}
Очки: {points}

Сделай МОТИВИРУЮЩЕЕ и КОНКРЕТНОЕ предсказание на месяц вперёд (3-4 предложения):
- Каким оператором/режиссёром он станет
- Какие навыки освоит
- Какой проект создаст

Пиши от души, с верой в успех, добавь эмодзи! Формат: просто текст без "предсказание:" и т.п."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты мудрый и мотивирующий наставник."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )
        
        return "🔮 ПРЕДСКАЗАНИЕ ОТ ГУРУ МЕДИА:\n\n" + response.choices[0].message.content
    except Exception as e:
        return "🔮 Магический шар затуманен... Попробуй позже!"

# ============== МОТИВАЦИОННЫЕ ЦИТАТЫ ==============

DAILY_QUOTES = [
    "🎬 'Кино — это правда 24 кадра в секунду' — Жан-Люк Годар",
    "
# ============== МОТИВАЦИОННЫЕ ЦИТАТЫ ==============

DAILY_QUOTES = [
    "🎬 'Кино — это правда 24 кадра в секунду' — Жан-Люк Годар",
    "📹 'Лучшая камера — та, что у тебя с собой' — Чейз Джарвис",
    "🎥 'Не снимай то, что видишь. Снимай то, что чувствуешь' — Дэвид Алан Харви",
    "✨ 'Креативность — это интеллект, который веселится' — Альберт Эйнштейн",
    "🔥 'Каждый эксперт когда-то был новичком' — Хелен Хейс",
    "🎯 'Не жди идеального момента. Создай его!' — Неизвестный",
    "💡 'Идеи без действий остаются просто мечтами' — Стив Джобс",
    "🌟 'Твой первый ролик будет плох. Снимай второй!' — Айра Гласс",
    "🚀 'Единственный способ делать великие вещи — любить то, что делаешь' — Стив Джобс",
    "📸 'Камера — это способ сохранить момент навсегда' — Неизвестный",
    "🎬 'Хороший фильм — это когда цена входного билета равна цене детской коляски' — Альфред Хичкок",
    "⚡ 'Не бойся совершенства — тебе его никогда не достичь' — Сальвадор Дали",
    "🎨 'Каждый художник сначала был любителем' — Ральф Эмерсон",
    "💪 'Мастерство — это тысяча повторений' — Японская пословица",
    "🌈 'Снимай в цвете, думай в черно-белом' — Неизвестный"
]

def get_daily_quote():
    random.seed(datetime.now().date().toordinal())
    return random.choice(DAILY_QUOTES)

# ============== СОБЫТИЯ ДНЯ ==============

DAILY_EVENTS = [
    {
        'name': '🎬 День оператора',
        'description': 'Сегодня x2 очков за все съёмочные задания!',
        'bonus': 'video_x2'
    },
    {
        'name': '📰 День журналиста',
        'description': 'Сегодня x2 очков за тесты и текстовые задания!',
        'bonus': 'text_x2'
    },
    {
        'name': '🎁 День щедрости',
        'description': 'Все сундуки дают в 2 раза больше наград!',
        'bonus': 'chest_x2'
    },
    {
        'name': '⚡ День энергии',
        'description': 'Энергия восстанавливается в 2 раза быстрее!',
        'bonus': 'energy_x2'
    },
    {
        'name': '🎯 День испытаний',
        'description': 'Новый мега-челлендж с крутыми призами!',
        'bonus': 'mega_challenge'
    },
    {
        'name': '🎰 День удачи',
        'description': 'Колесо фортуны можно крутить 3 раза!',
        'bonus': 'wheel_x3'
    },
    {
        'name': '🏆 Турнирный день',
        'description': 'Открыты дуэли! Сразись с другими учениками!',
        'bonus': 'duels_open'
    }
]

def get_daily_event():
    day_of_week = datetime.now().weekday()
    if day_of_week < len(DAILY_EVENTS):
        return DAILY_EVENTS[day_of_week]
    return None

# ============== СИСТЕМА СТАТИСТИКИ ==============

def init_user_stats(user_id):
    row = sql("SELECT user_id FROM user_stats WHERE user_id=?", (user_id,))
    if not row:
        sql("INSERT INTO user_stats(user_id) VALUES(?)", (user_id,))

def update_user_stats(user_id, points_delta=0):
    init_user_stats(user_id)
    sql("UPDATE user_stats SET total_points=total_points+? WHERE user_id=?", (points_delta, user_id))
    
    # Проверяем уровень
    row = sql("SELECT total_points, level FROM user_stats WHERE user_id=?", (user_id,))
    if row:
        pts, current_level = row
        for i, (threshold, title, desc) in enumerate(reversed(LEVELS)):
            if pts >= threshold:
                new_level = len(LEVELS) - i
                if new_level > current_level:
                    sql("UPDATE user_stats SET level=? WHERE user_id=?", (new_level, user_id))
                    try:
                        bot.send_message(user_id, 
                            f"🎉 ПОЗДРАВЛЯЮ!\n\n"
                            f"✨ Новый уровень: {new_level}\n"
                            f"{title}\n\n"
                            f"{desc}\n\n"
                            f"🔥 Так держать!")
                    except:
                        pass
                    
                    if new_level == 10:
                        unlock_achievement(user_id, 'level_10')
                break
    
    # Обновляем очки гильдии
    guild_row = sql("SELECT guild_id FROM user_stats WHERE user_id=?", (user_id,))
    if guild_row and guild_row[0]:
        sql("UPDATE guilds SET total_points=total_points+? WHERE guild_id=?", (points_delta, guild_row[0]))

def check_streak(user_id):
    init_user_stats(user_id)
    today = datetime.now().date().isoformat()
    now = datetime.now()
    row = sql("SELECT last_visit, streak_days FROM user_stats WHERE user_id=?", (user_id,))
    
    if row:
        last_visit, streak = row
        if last_visit:
            last_date = datetime.fromisoformat(last_visit).date()
            today_date = datetime.now().date()
            diff = (today_date - last_date).days
            
            if diff == 1:
                streak += 1
                sql("UPDATE user_stats SET streak_days=?, last_visit=? WHERE user_id=?", (streak, today, user_id))
                
                if streak == 3:
                    unlock_achievement(user_id, 'streak_3')
                elif streak == 7:
                    unlock_achievement(user_id, 'streak_7')
                elif streak == 30:
                    unlock_achievement(user_id, 'streak_30')
                
                return streak, True
            elif diff == 0:
                return streak, False
            else:
                sql("UPDATE user_stats SET streak_days=1, last_visit=? WHERE user_id=?", (today, user_id))
                return 1, True
        else:
            sql("UPDATE user_stats SET streak_days=1, last_visit=? WHERE user_id=?", (today, user_id))
            return 1, True
    
    # Проверяем ачивки по времени захода
    hour = now.hour
    if hour >= 0 and hour < 6:
        unlock_achievement(user_id, 'early_bird')
    elif hour >= 23 or hour < 1:
        unlock_achievement(user_id, 'night_owl')
    
    return 0, False

def unlock_achievement(user_id, ach_key):
    if ach_key not in ACHIEVEMENTS:
        return
    
    row = sql("SELECT achievements FROM user_stats WHERE user_id=?", (user_id,))
    if row:
        achs = row[0].split(',') if row[0] else []
        if ach_key not in achs:
            achs.append(ach_key)
            sql("UPDATE user_stats SET achievements=? WHERE user_id=?", (','.join(achs), user_id))
            emoji, desc = ACHIEVEMENTS[ach_key]
            try:
                bot.send_message(user_id, 
                    f"🏆 НОВАЯ АЧИВКА РАЗБЛОКИРОВАНА!\n\n"
                    f"{emoji}\n"
                    f"**{desc}**\n\n"
                    f"Смотри все ачивки: /profile")
            except:
                pass

def get_user_level_info(user_id):
    row = sql("SELECT total_points, level, streak_days, energy FROM user_stats WHERE user_id=?", (user_id,))
    if row:
        pts, lvl, streak, energy = row
        if lvl > len(LEVELS):
            lvl = len(LEVELS)
        level_title = LEVELS[lvl-1][1] if lvl <= len(LEVELS) else LEVELS[-1][1]
        next_threshold = LEVELS[lvl][0] if lvl < len(LEVELS) else "MAX"
        return pts, lvl, level_title, next_threshold, streak, energy
    return 0, 1, LEVELS[0][1], LEVELS[1][0], 0, 100

def claim_daily_reward(user_id):
    today = datetime.now().date().isoformat()
    row = sql("SELECT claimed FROM daily_rewards WHERE user_id=? AND date=?", (user_id, today))
    
    if row and row[0] == 1:
        return False, 0
    
    # Бонус за стрик
    streak_row = sql("SELECT streak_days FROM user_stats WHERE user_id=?", (user_id,))
    streak = streak_row[0] if streak_row else 1
    
    base_reward = 10
    streak_bonus = min(streak * 2, 50)  # Макс +50 за стрик
    total_reward = base_reward + streak_bonus
    
    sql("INSERT OR REPLACE INTO daily_rewards(user_id, date, claimed) VALUES(?,?,1)", (user_id, today))
    update_user_stats(user_id, total_reward)
    
    return True, total_reward, streak_bonus

# ============== ДУЭЛИ ==============

def create_duel(player1_id):
    # Находим случайного активного игрока
    candidates = sql("""SELECT user_id FROM user_stats 
                        WHERE user_id != ? 
                        AND last_visit >= date('now', '-7 days')
                        ORDER BY RANDOM() LIMIT 1""", (player1_id,))
    
    if not candidates:
        return None, "Пока нет активных соперников. Попробуй позже!"
    
    player2_id = candidates[0][0]
    
    duel_id = sql("""INSERT INTO duels(player1_id, player2_id, status, created_at) 
                     VALUES(?,?,'pending',?) RETURNING duel_id""", 
                  (player1_id, player2_id, datetime.now().isoformat()))
    
    try:
        bot.send_message(player2_id, 
            f"⚔️ ВЫЗОВ НА ДУЭЛЬ!\n\n"
            f"Игрок бросил тебе вызов!\n"
            f"Ответь на 3 вопроса быстрее соперника!\n\n"
            f"Принять? /duel_accept {duel_id[0]}")
    except:
        pass
    
    return duel_id[0], "Вызов отправлен! Жди ответа соперника..."

# ============== КРЕАТИВНЫЕ ЧЕЛЛЕНДЖИ ==============

DAILY_CHALLENGES = [
    "🎬 Сними 15-секундное видео с необычного ракурса",
    "📸 Сделай фото с идеальной композицией по правилу третей",
    "🎤 Возьми короткое интервью у друга о любимом хобби",
    "✨ Сними что-то красивое с естественным светом",
    "🎨 Создай коллаж из 3 кадров одного места",
    "🌅 Сними закат или рассвет с интересным передним планом",
    "🎭 Сними эмоцию крупным планом (радость, удивление, грусть)",
    "🏃 Сними видео в движении, используя стабилизацию",
    "🎪 Найди интересный паттерн или текстуру и сними её",
    "🌟 Сними силуэт на контрасте со светом",
    "🎬 Сними мини-историю из 3 кадров без слов",
    "🔊 Запиши чистый звук природы или города",
    "🎨 Используй цветовой контраст в кадре",
    "📐 Сними симметричную композицию",
    "🎭 Покажи одно место с разных точек зрения",
    "🌈 Сними отражение (в воде, зеркале, стекле)",
    "🔥 Покажи движение через серию фото",
    "🎯 Сними что-то через рамку (окно, дверь, арка)",
    "✨ Используй контровой свет для драмы",
    "🎪 Сними обычный предмет необычным способом"
]

def get_daily_challenge():
    random.seed(datetime.now().date().toordinal())
    return random.choice(DAILY_CHALLENGES)

# ============== КОНТЕНТ (чек-листы) ==============

checklist_text_ai = """
📝 **Чек-лист: Как написать закадровый текст с помощью ИИ**

Нейросети нужно дать четкий и подробный промпт. Следуй этому чек-листу:

**1. Основная информация о событии**
✅ Что это за событие?
✅ Когда и где?
✅ Кто организатор?
✅ Кто участники?
✅ Какова цель?

**2. Описание атмосферы**
✅ Какая была атмосфера?
✅ Что происходило?
✅ Какие эмоции?

**3. Итоги**
✅ Какое значение имело событие?
✅ Что сказали участники?

**4. Финальный промпт**
"Напиши закадровый текст для видеорепортажа о [событие]..."

✅ Готово! 🎬
"""

checklist_shooting = """
🎥 **Чек-лист для съёмки репортажа**

**1. Подготовка**
✅ Определите тему
✅ Исследуйте событие
✅ Составьте план
✅ Подготовьте вопросы
✅ Проверьте оборудование

**2. На съёмке**
✅ Общий план локации
✅ Детали и эмоции
✅ Интервью участников
✅ Проверка звука
✅ Несколько дублей
"""

interview_questions = """
🎤 **ТОП-10 вопросов для интервью**

1. Что вас привело сюда?
2. Какие эмоции испытываете?
3. Что самое интересное?
4. Оправдались ли ожидания?
5. Запомнившийся момент?
6. Опишите атмосферу словом
7. Совет тем, кто не пришёл?
8. Планы на будущее?
9. Что бы изменили?
10. Пожелания организаторам?

💡 Задавай открытые вопросы!
"""

composition_rules = """
📐 **Основы композиции**

1. **Правило третей** - объект на пересечениях
2. **Диагонали** - динамика кадра
3. **Симметрия** - гармония
4. **Рамка в кадре** - глубина
5. **Ведущие линии** - фокус
6. **Пространство** - направление движения
7. **Точка съёмки** - меняет восприятие

🎬 Правила созданы, чтобы их нарушать!
"""

resources_text = """
🌐 **Полезные ресурсы**

📺 Каналы:
• МЕДИАЦЕНТР МАРФИНО: https://www.youtube.com/@-m50
• ПОЛЕЗНЫЙ БЛОГ: https://www.youtube.com/@%D0%9F%D0%BE%D0%BB%D0%B5%D0%B7%D0%BD%D1%8B%D0%B9%D0%B1%D0%BB%D0%BE%D0%B3

👥 Сообщества:
• ВК ДК Марфино: https://vk.com/dkmarfino
• aXIS: https://vk.com/axisskill

Подписывайся! 🚀
"""

courses_text = """
🎓 **Курсы aXIS**

🌐 https://artmediaskill.ru/

✨ БЕСПЛАТНЫЕ курсы по:
• Видеосъёмке
• Журналистике
• Нейросетям
• Блогингу
• Режиссуре

💬 Нужна помощь? Спроси!
"""

# ============== МЕНЮ ==============

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('🎲 Рулетка'), KeyboardButton('👤 Профиль'))
    markup.add(KeyboardButton('📚 Чек-листы'), KeyboardButton('🎯 Тесты'))
    markup.add(KeyboardButton('⚔️ Квесты'), KeyboardButton('💡 Идея дня'))
    markup.add(KeyboardButton('🌐 Ресурсы'), KeyboardButton('💬 ИИ'))
    return markup

def checklists_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('📝 Текст с ИИ', callback_data='check_ai_text'),
        InlineKeyboardButton('🎥 Съёмка', callback_data='check_shooting'),
        InlineKeyboardButton('🎤 Интервью', callback_data='check_interview'),
        InlineKeyboardButton('📐 Композиция', callback_data='check_composition'),
        InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
    )
    return markup

def tests_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🎬 Видеосъёмка', callback_data='test_video'),
        InlineKeyboardButton('📰 Журналистика', callback_data='test_journalism'),
        InlineKeyboardButton('📝 Мини-тест', callback_data='minitest_week'),
        InlineKeyboardButton('🧠 Квиз', callback_data='quiz_week'),
        InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
    )
    return markup

def resources_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton('🌐 Ресурсы', callback_data='resources'),
        InlineKeyboardButton('🎓 Курсы', callback_data='courses'),
        InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
    )
    return markup

def profile_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('🏆 Ачивки', callback_data='achievements'),
        InlineKeyboardButton('📊 Топ-10', callback_data='leaderboard'),
        InlineKeyboardButton('🎁 Награда дня', callback_data='daily_reward'),
        InlineKeyboardButton('📦 Сундуки', callback_data='my_chests'),
        InlineKeyboardButton('🔮 Предсказание', callback_data='prediction'),
        InlineKeyboardButton('⚔️ Дуэль', callback_data='start_duel'),
        InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
    )
    return markup

def quests_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=1)
    
    for qid, qdata in QUESTS.items():
        row = sql("SELECT completed FROM user_quests WHERE user_id=? AND quest_id=?", (user_id, qid))
        status = "✅" if row and row[0] == 1 else "🎯"
        markup.add(InlineKeyboardButton(f"{status} {qdata['title']}", callback_data=f'quest_{qid}'))
    
    markup.add(InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
    return markup

# ============== СОСТОЯНИЯ ==============
user_states = {}
user_data = {}

video_questions = [
    ("1/5: Что лучше для стабильного видео?", 
     ['A: Держать рукой', 'B: Штатив', 'C: Бежать'], 'B'),
    ("2/5: Какой план показывает общее место?", 
     ['A: Общий', 'B: Крупный', 'C: Средний'], 'A'),
    ("3/5: Звук на шумном мероприятии?", 
     ['A: Игнорировать', 'B: Встроенный', 'C: Внешний микрофон'], 'C'),
    ("4/5: Как избежать тряски?", 
     ['A: Бежать', 'B: Дышать спокойно', 'C: Повороты'], 'B'),
    ("5/5: Зачем проверять оборудование?", 
     ['A: Не забыть зарядку', 'B: Время', 'C: Круто'], 'A')
]

journalism_questions = [
    ("1/5: Что входит в 5W?", 
     ['A: 2 пункта', 'B: 3 пункта', 'C: Who, What, When, Where, Why'], 'C'),
    ("2/5: Как писать заголовок?", 
     ['A: Длинный', 'B: Краткий', 'C: Без слов'], 'B'),
    ("3/5: Закадровый текст это?", 
     ['A: Голос за кадром', 'B: Интервью', 'C: Текст'], 'A'),
    ("4/5: Подготовка к интервью?", 
     ['A: Не думать', 'B: Любые вопросы', 'C: Список заранее'], 'C'),
    ("5/5: Зачем атмосфера?", 
     ['A: Заполнить', 'B: Передать эмоции', 'C: Длиннее'], 'B')
]

def is_user_in_db(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def show_menu_and_greeting(message):
    user_id = message.chat.id
    
    # Проверяем стрик
    streak, is_new = check_streak(user_id)
    
    # Получаем инфо
    pts, lvl, title, next_pts, streak, energy = get_user_level_info(user_id)
    
    # Событие дня
    event = get_daily_event()
    event_text = f"\n\n🎪 {event['name']}\n{event['description']}" if event else ""
    
    # Цитата дня
    quote = get_daily_quote()
    
    greeting = (
        f'🎬 **ЙО, КРЕАТИВНЫЙ ГЕНИЙ!**\n\n'
        f'Я твой помощник в медиацентре Марфино!\n\n'
        f'👤 Уровень: {lvl} — {title}\n'
        f'⭐ Очки: {pts}/{next_pts}\n'
        f'🔥 Стрик: {streak} дн.\n'
        f'⚡ Энергия: {energy}/100'
        f'{event_text}\n\n'
        f'💭 {quote}\n\n'
        f'🎯 Выбирай активность в меню!'
    )
    
    bot.send_message(user_id, greeting, reply_markup=main_menu(), parse_mode='Markdown')

# ============== КОМАНДЫ ==============

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if is_user_in_db(user_id):
        show_menu_and_greeting(message)
        return

    bot.send_message(user_id, '🎬 Йо! Я бот медиацентра Марфино. Как тебя зовут?')
    user_states[user_id] = 'waiting_name'
    user_data[user_id] = {'name': '', 'experience': '', 'interests': []}

@bot.message_handler(commands=['profile'])
def cmd_profile(message):
    user_id = message.from_user.id
    pts, lvl, title, next_pts, streak, energy = get_user_level_info(user_id)
    
    # Ачивки
    ach_row = sql("SELECT achievements FROM user_stats WHERE user_id=?", (user_id,))
    achs = ach_row[0].split(',') if ach_row and ach_row[0] else []
    ach_count = len([a for a in achs if a])
    
    # Квесты
    quests_done = sql("SELECT COUNT(*) FROM user_quests WHERE user_id=? AND completed=1", (user_id,))
    quests_count = quests_done[0] if quests_done else 0
    
    # Сундуки
    chests_count = sql("SELECT COUNT(*) FROM chests WHERE user_id=? AND opened=0", (user_id,))
    chests = chests_count[0] if chests_count else 0
    
    profile_text = (
        f"👤 **ТВОЙ ПРОФИЛЬ**\n\n"
        f"🏅 Уровень: {lvl} — {title}\n"
        f"⭐ Очки: {pts}/{next_pts}\n"
        f"🔥 Стрик: {streak} дней\n"
        f"⚡ Энергия: {energy}/100\n\n"
        f"🏆 Ачивки: {ach_count}/{len(ACHIEVEMENTS)}\n"
        f"⚔️ Квесты: {quests_count}\n"
        f"📦 Сундуки: {chests}\n\n"
        f"Прогресс до уровня {lvl+1}: {pts}/{next_pts} ({int(pts/next_pts*100) if next_pts != 'MAX' else 100}%)"
    )
    
    bot.send_message(user_id, profile_text, reply_markup=profile_menu(user_id), parse_mode='Markdown')

@bot.message_handler(commands=['quests'])
def cmd_quests(message):
    bot.send_message(message.chat.id, "⚔️ **ДОСТУПНЫЕ КВЕСТЫ**\n\nВыбери квест:", 
                     reply_markup=quests_menu(message.from_user.id), parse_mode='Markdown')

@bot.message_handler(commands=['week'])
def cmd_week(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Пока нет активного задания недели.")
        return
    row = get_task(wid)
    if not row:
        bot.send_message(message.chat.id, "Задание недели ещё не настроено.")
        return
    bot.send_message(message.chat.id, format_task_text(row))

@bot.message_handler(commands=['myrank'])
def cmd_myrank(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Сейчас нет активной недели.")
        return
    pts = get_points(message.from_user.id, wid)
    bot.send_message(message.chat.id, f"👤 Твой счёт за {wid}: {pts} очков")

@bot.message_handler(commands=['rank'])
def cmd_rank(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Сейчас нет активной недели.")
        return
    rows = top_week(wid, 10)
    if not rows:
        bot.send_message(message.chat.id, "Пока нет участников. Будь первым!")
        return
    medals = ["🥇","🥈","🥉"]
    lines = []
    for i,(uid,pts) in enumerate(rows, start=1):
        # Получаем имя
        name_row = sql("SELECT name FROM users WHERE user_id=?", (uid,))
        name = name_row[0] if name_row else f"ID{uid}"
        mark = medals[i-1] if i<=3
        mark = medals[i-1] if i<=3 else f"{i}."
        lines.append(f"{mark} {name} — {pts} очков")
    bot.send_message(message.chat.id, f"🏆 **Топ-10 за {wid}:**\n\n" + "\n".join(lines), parse_mode='Markdown')

# ============== КОМАНДЫ УЧИТЕЛЯ ==============

@bot.message_handler(commands=['setweek'])
def cmd_setweek(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    text = message.text[len('/setweek'):].strip()
    if not text:
        bot.send_message(message.chat.id,
            "Формат:\n/setweek 2025-W40 | Название | Описание | https://ссылка | дедлайн")
        return
    parts = [p.strip() for p in text.split('|')]
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Минимум 3 части: WEEK_ID | Название | Описание")
        return
    week_id = parts[0]
    title = parts[1]
    descr = parts[2]
    link = parts[3] if len(parts)>=4 else ""
    deadline = parts[4] if len(parts)>=5 else ""
    upsert_task(week_id, 'media', title, descr, link, deadline)
    set_current_week(week_id)
    bot.send_message(message.chat.id, f"✅ Задание недели {week_id} установлено!\n\n{format_task_text(get_task(week_id))}")

@bot.message_handler(commands=['kind'])
def cmd_kind(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    text = message.text.strip().split()
    if len(text)<2 or text[1] not in ('media','quiz','minitest'):
        bot.send_message(message.chat.id, "Используй: /kind media | quiz | minitest")
        return
    if set_kind(text[1]):
        bot.send_message(message.chat.id, f"✅ Тип: {text[1]}")
    else:
        bot.send_message(message.chat.id, "Сначала /setweek")

@bot.message_handler(commands=['sendweek'])
def cmd_sendweek(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Только для учителя.")
        return
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет активной недели.")
        return
    row = get_task(wid)
    if not row:
        bot.send_message(message.chat.id, "Задание не настроено.")
        return
    text = "🎮 **НОВОЕ ЗАДАНИЕ НЕДЕЛИ!**\n\n" + format_task_text(row)
    ids = users_all_ids()
    sent = 0
    for uid in ids:
        try:
            bot.send_message(uid, text, parse_mode='Markdown')
            sent += 1
        except:
            pass
    bot.send_message(message.chat.id, f"Отправлено {sent} ученикам!")

@bot.message_handler(commands=['award'])
def cmd_award(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Только для учителя.")
        return
    parts = message.text.strip().split()
    if len(parts)<3:
        bot.send_message(message.chat.id, "Формат: /award <user_id> <очки>")
        return
    try:
        uid = int(parts[1]); pts = int(parts[2])
    except:
        bot.send_message(message.chat.id, "user_id и очки - числа")
        return
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет недели. /setweek")
        return
    add_points(uid, wid, pts)
    bot.send_message(message.chat.id, f"✅ +{pts} очков для ID {uid}")

@bot.message_handler(commands=['summary'])
def cmd_summary(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Только для учителя.")
        return
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет недели.")
        return
    rows = top_week(wid, 10)
    if not rows:
        bot.send_message(message.chat.id, "Никто не участвовал.")
        return
    medals = ["🥇","🥈","🥉"]
    lines = []
    for i,(uid,pts) in enumerate(rows, start=1):
        name_row = sql("SELECT name FROM users WHERE user_id=?", (uid,))
        name = name_row[0] if name_row else f"ID{uid}"
        mark = medals[i-1] if i<=3 else f"{i}."
        lines.append(f"{mark} {name} — {pts} очков")
    text = f"🎺 **УРА! ИТОГИ {wid}**\n\n" + "\n".join(lines) + f"\n\n⭐ Звезда недели — {rows[0][0]}!"
    ids = users_all_ids()
    for uid in ids:
        try:
            bot.send_message(uid, text, parse_mode='Markdown')
        except:
            pass
    bot.send_message(message.chat.id, "Итоги разосланы! ⭐")

@bot.message_handler(commands=['setquiz'])
def cmd_setquiz(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Только для учителя.")
        return
    txt = message.text[len('/setquiz'):].strip()
    parts = [p.strip() for p in txt.split('|')]
    if len(parts) < 5:
        bot.send_message(message.chat.id, "Формат: /setquiz Вопрос | A | B | C | индекс(0-2)")
        return
    q, a, b, c, idx = parts[0], parts[1], parts[2], parts[3], parts[4]
    try:
        idx = int(idx)
        if idx not in (0,1,2): raise ValueError
    except:
        bot.send_message(message.chat.id, "Индекс 0-2")
        return
    if not set_quiz(q, a, b, c, idx):
        bot.send_message(message.chat.id, "Сначала /setweek и /kind quiz")
        return
    bot.send_message(message.chat.id, "✅ Квиз сохранён. /quiz для учеников")

@bot.message_handler(commands=['quiz'])
def cmd_quiz(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет недели.")
        return
    row = get_task(wid)
    if not row or row[1] != 'quiz' or not row[6]:
        bot.send_message(message.chat.id, "Квиз не настроен.")
        return
    _,_,_,_,_,_, qq, qa, qb, qc, correct = row
    try:
        bot.send_poll(
            message.chat.id,
            question="🧠 Квиз недели: " + qq,
            options=[qa, qb, qc],
            type="quiz",
            correct_option_id=correct,
            is_anonymous=False,
            explanation="Проверь урок! 😉"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    option_ids = poll_answer.option_ids
    if not option_ids:
        return
    wid = get_current_week()
    if not wid:
        return
    row = get_task(wid)
    if not row or row[1] != 'quiz' or row[10] is None:
        return
    correct = row[10]
    chosen = option_ids[0]
    if chosen == correct and not already_awarded(user_id, wid, 'quiz'):
        add_points(user_id, wid, POINTS_QUIZ_RIGHT)
        mark_awarded(user_id, wid, 'quiz')
        unlock_achievement(user_id, 'quiz_master')
        update_quest_progress(user_id, 'quiz')
        try:
            bot.send_message(user_id, f"✅ Правильно! +{POINTS_QUIZ_RIGHT} очков! /myrank")
        except:
            pass

@bot.message_handler(commands=['minitest'])
def cmd_minitest(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет недели.")
        return
    row = get_task(wid)
    if not row or row[1] != 'minitest':
        bot.send_message(message.chat.id, "Мини-тест не активен.")
        return
    sql("INSERT OR REPLACE INTO weekly_test_states(user_id,week_id,q_index,score) VALUES(?,?,0,0)",
        (message.from_user.id, wid))
    q, opts, _ = MINITEST_QUESTIONS[0]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for o in opts: kb.add(KeyboardButton(o))
    bot.send_message(message.chat.id, "📝 **Мини-тест (3 вопроса)**\n\nВопрос 1/3:\n" + q, reply_markup=kb, parse_mode='Markdown')

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, 'Только для учителя.')
        return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.send_message(message.chat.id, 'Напиши текст после команды')
        return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for row in users:
        try:
            bot.send_message(row[0], text, parse_mode='Markdown')
            sent += 1
        except:
            pass
    bot.send_message(message.chat.id, f'Отправлено {sent} ученикам!')

@bot.message_handler(commands=['listusers'])
def list_users(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, 'Только для учителя.')
        return
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    if not users:
        bot.send_message(message.chat.id, 'Нет учеников.')
        return
    list_text = "**СПИСОК УЧЕНИКОВ:**\n\n"
    for row in users:
        list_text += f"ID: {row[0]}\nИмя: {row[1]}\nОпыт: {row[2]}\nИнтересы: {row[3]}\n\n"
    bot.send_message(message.chat.id, list_text, parse_mode='Markdown')

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.send_message(message.chat.id, f'Твой ID: `{message.chat.id}`', parse_mode='Markdown')

# ============== ОБРАБОТКА МЕДИА #challenge ==============

@bot.message_handler(content_types=['photo','video'])
def handle_media_challenge(message):
    caption = (message.caption or "").lower()
    if "#challenge" not in caption:
        return
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет недели. /setweek")
        return
    row = get_task(wid)
    if not row or row[1] != 'media':
        bot.send_message(message.chat.id, "Сейчас не медиа-неделя. /week")
        return

    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        ftype = 'photo'
    else:
        file_id = message.video.file_id
        ftype = 'video'

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql("""INSERT INTO weekly_submissions(user_id,week_id,file_id,file_type,caption,ts)
           VALUES(?,?,?,?,?,?)""", (message.from_user.id, wid, file_id, ftype, message.caption or "", ts))

    # Обновляем счётчик видео
    sql("UPDATE user_stats SET videos_submitted=videos_submitted+1 WHERE user_id=?", (message.from_user.id,))

    if not already_awarded(message.from_user.id, wid, 'media'):
        add_points(message.from_user.id, wid, POINTS_MEDIA_FIRST)
        mark_awarded(message.from_user.id, wid, 'media')
        unlock_achievement(message.from_user.id, 'first_challenge')
        update_quest_progress(message.from_user.id, 'challenge')
        bot.send_message(message.chat.id, f"✅ Принято! +{POINTS_MEDIA_FIRST} очков! /myrank")
    else:
        bot.send_message(message.chat.id, "✅ Работа сохранена!")
    
    # Проверяем ачивку креатора
    vid_count = sql("SELECT videos_submitted FROM user_stats WHERE user_id=?", (message.from_user.id,))
    if vid_count and vid_count[0] >= 10:
        unlock_achievement(message.from_user.id, 'content_creator')

# ============== CALLBACK ОБРАБОТЧИК ==============

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.message.chat.id
    
    try:
        if call.data == 'main_menu':
            bot.edit_message_text('🎬 Главное меню:', user_id, call.message.message_id)
            bot.send_message(user_id, 'Выбирай:', reply_markup=main_menu())
        
        # ========== ЧЕК-ЛИСТЫ ==========
        elif call.data == 'checklists':
            bot.edit_message_text('📚 Чек-листы и подсказки:', user_id, call.message.message_id, reply_markup=checklists_menu())
        
        elif call.data == 'check_ai_text':
            bot.send_message(user_id, checklist_text_ai, parse_mode='Markdown')
            update_quest_progress(user_id, 'checklist', 'check_ai_text')
            bot.answer_callback_query(call.id, "✅ Чек-лист отправлен!")
        
        elif call.data == 'check_shooting':
            bot.send_message(user_id, checklist_shooting, parse_mode='Markdown')
            update_quest_progress(user_id, 'checklist', 'check_shooting')
            bot.answer_callback_query(call.id, "✅ Чек-лист отправлен!")
        
        elif call.data == 'check_interview':
            bot.send_message(user_id, interview_questions, parse_mode='Markdown')
            update_quest_progress(user_id, 'checklist', 'check_interview')
            bot.answer_callback_query(call.id, "✅ Вопросы отправлены!")
        
        elif call.data == 'check_composition':
            bot.send_message(user_id, composition_rules, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Подсказка отправлена!")
        
        # ========== ТЕСТЫ ==========
        elif call.data == 'tests':
            bot.edit_message_text('🎯 Тесты и квизы:', user_id, call.message.message_id, reply_markup=tests_menu())
        
        elif call.data == 'test_video':
            if not is_user_in_db(user_id):
                bot.answer_callback_query(call.id, "❌ Сначала /start")
                return
            
            # Проверяем энергию
            can_use, energy = use_energy(user_id, 10)
            if not can_use:
                bot.answer_callback_query(call.id, f"⚡ Недостаточно энергии! Осталось: {energy}")
                return
            
            user_states[user_id] = 'test_video_q1'
            user_data[user_id] = {'score': 0, 'questions': video_questions, 'start_time': datetime.now()}
            q, options, _ = video_questions[0]
            options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            options_menu.add(*[KeyboardButton(opt) for opt in options])
            bot.send_message(user_id, "🎬 **ТЕСТ: ВИДЕОСЪЁМКА**\n\n" + q, reply_markup=options_menu, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Тест запущен! -10 энергии")
        
        elif call.data == 'test_journalism':
            if not is_user_in_db(user_id):
                bot.answer_callback_query(call.id, "❌ Сначала /start")
                return
            
            can_use, energy = use_energy(user_id, 10)
            if not can_use:
                bot.answer_callback_query(call.id, f"⚡ Недостаточно энергии! Осталось: {energy}")
                return
            
            user_states[user_id] = 'test_journalism_q1'
            user_data[user_id] = {'score': 0, 'questions': journalism_questions, 'start_time': datetime.now()}
            q, options, _ = journalism_questions[0]
            options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            options_menu.add(*[KeyboardButton(opt) for opt in options])
            bot.send_message(user_id, "📰 **ТЕСТ: ЖУРНАЛИСТИКА**\n\n" + q, reply_markup=options_menu, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Тест запущен! -10 энергии")
        
        elif call.data == 'minitest_week':
            cmd_minitest(call.message)
            bot.answer_callback_query(call.id)
        
        elif call.data == 'quiz_week':
            cmd_quiz(call.message)
            bot.answer_callback_query(call.id)
        
        # ========== РЕСУРСЫ ==========
        elif call.data == 'resources_menu':
            bot.edit_message_text('🌐 Ресурсы:', user_id, call.message.message_id, reply_markup=resources_menu())
        
        elif call.data == 'resources':
            bot.send_message(user_id, resources_text, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Отправлено!")
        
        elif call.data == 'courses':
            bot.send_message(user_id, courses_text, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Отправлено!")
        
        # ========== ПРОФИЛЬ ==========
        elif call.data == 'achievements':
            ach_row = sql("SELECT achievements FROM user_stats WHERE user_id=?", (user_id,))
            achs = ach_row[0].split(',') if ach_row and ach_row[0] else []
            
            text = "🏆 **ТВОИ АЧИВКИ:**\n\n"
            unlocked = []
            locked = []
            
            for key, (emoji, desc) in ACHIEVEMENTS.items():
                if key in achs:
                    unlocked.append(f"✅ {emoji} {desc}")
                else:
                    locked.append(f"🔒 {desc}")
            
            text += "\n".join(unlocked) if unlocked else "Пока нет ачивок"
            text += f"\n\n**Заблокировано ({len(locked)}):**\n"
            text += "\n".join(locked[:5]) + ("\n..." if len(locked) > 5 else "")
            
            bot.send_message(user_id, text, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        
        elif call.data == 'leaderboard':
            # Общий топ по очкам
            rows = sql("""SELECT u.name, s.total_points 
                          FROM user_stats s 
                          JOIN users u ON s.user_id=u.user_id 
                          ORDER BY s.total_points DESC LIMIT 10""", many=True)
            
            if not rows:
                bot.answer_callback_query(call.id, "Нет данных")
                return
            
            medals = ["🥇","🥈","🥉"]
            lines = []
            for i, (name, pts) in enumerate(rows, start=1):
                mark = medals[i-1] if i<=3 else f"{i}."
                lines.append(f"{mark} {name} — {pts} очков")
            
            text = "🏆 **ТОП-10 ВСЕХ ВРЕМЁН:**\n\n" + "\n".join(lines)
            bot.send_message(user_id, text, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        
        elif call.data == 'daily_reward':
            success, reward, *bonus = claim_daily_reward(user_id)
            if success:
                streak_bonus = bonus[0] if bonus else 0
                text = f"🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**\n\n💰 +{reward} очков\n"
                if streak_bonus > 0:
                    text += f"🔥 Бонус за стрик: +{streak_bonus}\n"
                text += "\nПриходи завтра за новой наградой!"
                bot.send_message(user_id, text, parse_mode='Markdown')
                bot.answer_callback_query(call.id, "✅ Награда получена!")
            else:
                bot.answer_callback_query(call.id, "⏰ Ты уже забрал награду сегодня!")
        
        elif call.data == 'my_chests':
            chests = sql("""SELECT chest_type, COUNT(*) 
                            FROM chests 
                            WHERE user_id=? AND opened=0 
                            GROUP BY chest_type""", (user_id,), many=True)
            
            if not chests:
                bot.send_message(user_id, "📦 У тебя пока нет сундуков!\n\nПолучай их из колеса удачи! 🎰")
                bot.answer_callback_query(call.id)
                return
            
            text = "📦 **ТВОИ СУНДУКИ:**\n\n"
            chest_emojis = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇'}
            
            markup = InlineKeyboardMarkup(row_width=1)
            for chest_type, count in chests:
                emoji = chest_emojis.get(chest_type, '📦')
                text += f"{emoji} {chest_type.capitalize()}: {count} шт.\n"
                markup.add(InlineKeyboardButton(f"Открыть {chest_type}", callback_data=f'open_{chest_type}'))
            
            markup.add(InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
            bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        
        elif call.data.startswith('open_'):
            chest_type = call.data.replace('open_', '')
            success, result = open_chest(user_id, chest_type)
            if success:
                bot.send_message(user_id, result, parse_mode='Markdown')
                bot.answer_callback_query(call.id, "✨ Сундук открыт!")
            else:
                bot.answer_callback_query(call.id, result)
        
        elif call.data == 'prediction':
            prediction = generate_prediction(user_id)
            bot.send_message(user_id, prediction, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "🔮 Предсказание готово!")
        
        elif call.data == 'start_duel':
            duel_id, msg = create_duel(user_id)
            bot.send_message(user_id, msg)
            bot.answer_callback_query(call.id)
        
        # ========== КВЕСТЫ ==========
        elif call.data.startswith('quest_'):
            quest_id = call.data.replace('quest_', '')
            qdata = QUESTS.get(quest_id)
            if not qdata:
                bot.answer_callback_query(call.id, "Квест не найден")
                return
            
            # Проверяем статус
            row = sql("SELECT progress, completed FROM user_quests WHERE user_id=? AND quest_id=?", (user_id, quest_id))
            
            if row and row[1] == 1:
                status_text = "✅ **ЗАВЕРШЁН!**"
            elif row:
                progress = json.loads(row[0]) if row[0] else {}
                completed_tasks = sum(1 for k, v in progress.items() if not k.endswith('_count') and v)
                total_tasks = len(qdata['tasks'])
                status_text = f"📊 Прогресс: {completed_tasks}/{total_tasks}"
            else:
                status_text = "🎯 **Не начат**"
            
            text = f"⚔️ **{qdata['title']}**\n\n{qdata['description']}\n\n**Задания:**\n"
            for i, task in enumerate(qdata['tasks']):
                if row and row[0]:
                    progress = json.loads(row[0])
                    done = progress.get(f"task_{i}", False)
                    mark = "✅" if done else "⏳"
                else:
                    mark = "⏳"
                text += f"{mark} {task['desc']}\n"
            
            text += f"\n{status_text}\n\n🎁 Награда: {qdata['reward_points']} очков"
            
            markup = InlineKeyboardMarkup()
            if not row or row[1] == 0:
                markup.add(InlineKeyboardButton('🎯 Начать квест', callback_data=f'start_quest_{quest_id}'))
            markup.add(InlineKeyboardButton('🔙 Назад', callback_data='quests_list'))
            
            bot.edit_message_text(text, user_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        
        elif call.data.startswith('start_quest_'):
            quest_id = call.data.replace('start_quest_', '')
            success, msg = start_quest(user_id, quest_id)
            bot.answer_callback_query(call.id, msg)
            if success:
                bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
        
        elif call.data == 'quests_list':
            bot.edit_message_text("⚔️ **ДОСТУПНЫЕ КВЕСТЫ**\n\nВыбери квест:", 
                                 user_id, call.message.message_id, 
                                 reply_markup=quests_menu(user_id), parse_mode='Markdown')
    
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")

# ============== ОБРАБОТКА ТЕКСТА ==============

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text.strip()

    # ==== Мини-тест недели ====
    wid = get_current_week()
    if wid:
        st = sql("SELECT q_index,score FROM weekly_test_states WHERE user_id=? AND week_id=?", (user_id, wid))
        if st:
            q_index, score = st
            if text and text[0] in ('A','B','C'):
                correct = MINITEST_QUESTIONS[q_index][2]
                if text[0] == correct:
                    score += 1
                q_index += 1
                if q_index < 3:
                    sql("UPDATE weekly_test_states SET q_index=?,score=? WHERE user_id=? AND week_id=?",
                        (q_index, score, user_id, wid))
                    q, opts, _ = MINITEST_QUESTIONS[q_index]
                    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    for o in opts: kb.add(KeyboardButton(o))
                    bot.send_message(user_id, f"Вопрос {q_index+1}/3:\n{q}", reply_
                    bot.send_message(user_id, f"Вопрос {q_index+1}/3:\n{q}", reply_markup=kb)
                    return
                else:
                    sql("DELETE FROM weekly_test_states WHERE user_id=? AND week_id=?", (user_id, wid))
                    if not already_awarded(user_id, wid, 'minitest'):
                        pts = POINTS_MINITEST.get(score, 0)
                        add_points(user_id, wid, pts)
                        mark_awarded(user_id, wid, 'minitest')
                        bot.send_message(user_id, f"✅ **Тест завершён!**\n\nПравильно: {score}/3\n+{pts} очков\n\n/myrank", 
                                       reply_markup=main_menu(), parse_mode='Markdown')
                    else:
                        bot.send_message(user_id, f"Тест завершён: {score}/3\nОчки уже начислены. /myrank", 
                                       reply_markup=main_menu())
                    return

    # ==== ОНБОРДИНГ ====
    if user_id in user_states and 'waiting_' in user_states[user_id]:
        state = user_states[user_id]

        if state == 'waiting_name':
            user_data[user_id]['name'] = text
            yes_no_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            yes_no_menu.add(KeyboardButton('Да'), KeyboardButton('Нет'))
            bot.send_message(user_id, f'Круто, {text}! 😎\n\nРазрешаешь добавить тебя в базу учеников? Это поможет мне персонализировать контент!', 
                           reply_markup=yes_no_menu)
            user_states[user_id] = 'waiting_permission'

        elif state == 'waiting_permission':
            if text.lower() == 'да':
                experience_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                experience_menu.add(KeyboardButton('До 1 года'), KeyboardButton('Больше 1 года'))
                bot.send_message(user_id, 'Отлично! Небольшая анкета.\n\nСколько ты посещаешь медиацентр Марфино?', 
                               reply_markup=experience_menu)
                user_states[user_id] = 'waiting_experience'
            elif text.lower() == 'нет':
                del user_states[user_id]
                del user_data[user_id]
                bot.send_message(user_id, 'Ок, без проблем! Давай сразу к делу.')
                show_menu_and_greeting(message)
            else:
                bot.send_message(user_id, 'Выбери "Да" или "Нет".')

        elif state == 'waiting_experience':
            user_data[user_id]['experience'] = text
            interests_menu = ReplyKeyboardMarkup(resize_keyboard=True)
            interests_menu.add(KeyboardButton('Снимать видео'), KeyboardButton('Режиссура'))
            interests_menu.add(KeyboardButton('Журналистика'), KeyboardButton('Блогинг'))
            interests_menu.add(KeyboardButton('Нейросети'), KeyboardButton('Готово'))
            bot.send_message(user_id, 'Что интересует? (Выбери несколько, потом "Готово")', 
                           reply_markup=interests_menu)
            user_states[user_id] = 'waiting_interests'

        elif state == 'waiting_interests':
            if text == 'Готово':
                interests_str = ', '.join(user_data[user_id]['interests'])
                summary = (f"**Проверь анкету:**\n\n"
                          f"Имя: {user_data[user_id]['name']}\n"
                          f"Опыт: {user_data[user_id]['experience']}\n"
                          f"Интересы: {interests_str if interests_str else 'Не указано'}")
                confirm_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                confirm_menu.add(KeyboardButton('Да, верно'), KeyboardButton('Начать заново'))
                bot.send_message(user_id, summary + '\n\nВсё правильно?', reply_markup=confirm_menu, parse_mode='Markdown')
                user_states[user_id] = 'waiting_confirm'
            else:
                if text not in user_data[user_id]['interests']:
                    user_data[user_id]['interests'].append(text)
                bot.send_message(user_id, f'Добавил: {text}. Выбери ещё или "Готово".')

        elif state == 'waiting_confirm':
            if text == 'Да, верно':
                interests_str = ', '.join(user_data[user_id]['interests'])
                cursor.execute("INSERT INTO users (user_id, name, experience, interests) VALUES (?, ?, ?, ?)",
                             (user_id, user_data[user_id]['name'], user_data[user_id]['experience'], interests_str))
                conn.commit()
                
                # Инициализируем статистику
                init_user_stats(user_id)
                
                bot.send_message(user_id, '🎉 Супер, сохранено!\n\n🎁 Бонус новичка: +20 очков!')
                update_user_stats(user_id, 20)
                
                del user_states[user_id]
                del user_data[user_id]
                show_menu_and_greeting(message)
            elif text == 'Начать заново':
                bot.send_message(user_id, 'Ок, давай заново. Как тебя зовут?')
                user_states[user_id] = 'waiting_name'
                user_data[user_id] = {'name': '', 'experience': '', 'interests': []}
            else:
                bot.send_message(user_id, 'Выбери "Да, верно" или "Начать заново".')

        return

    # ==== ОБРАБОТКА ТЕСТОВ ====
    if user_id in user_states and 'test_' in user_states[user_id]:
        state = user_states[user_id]
        test_type, q_num = state.rsplit('_q', 1)
        q_index = int(q_num) - 1
        questions = user_data[user_id]['questions']
        _, _, correct = questions[q_index]

        answer_letter = text[0] if text else ''
        if answer_letter == correct:
            user_data[user_id]['score'] += 1

        if q_index < 4:  # Следующий вопрос
            next_state = f'{test_type}_q{q_index + 2}'
            user_states[user_id] = next_state
            q, options, _ = questions[q_index + 1]
            options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            options_menu.add(*[KeyboardButton(opt) for opt in options])
            bot.send_message(user_id, q, reply_markup=options_menu)
        else:  # Конец теста
            score = user_data[user_id]['score']
            
            # Проверяем время прохождения
            start_time = user_data[user_id].get('start_time')
            if start_time:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed < 60:
                    unlock_achievement(user_id, 'speed_demon')
            
            # Проверяем перфекта
            if score == 5:
                unlock_achievement(user_id, 'perfectionist')
            
            # Выдаём очки
            points = score * 5
            update_user_stats(user_id, points)
            
            # Обновляем квест
            test_name = 'video' if 'video' in test_type else 'journalism'
            update_quest_progress(user_id, 'test', test_name)
            unlock_achievement(user_id, 'first_test')
            
            if score <= 2:
                verdict = "🌱 Ты только начинаешь, но в медиацентре ты всему научишься! Приходи на уроки!"
            elif score <= 4:
                verdict = "⚡ Хорошо, но есть куда расти! Приходи на занятия!"
            else:
                verdict = "🏆 Супер, ты уже мастер! Продолжай практиковать и создавай крутые видео!"

            result_text = (f"🎯 **РЕЗУЛЬТАТ ТЕСТА**\n\n"
                          f"Правильно: {score}/5\n"
                          f"💰 Очки: +{points}\n\n"
                          f"{verdict}")
            
            bot.send_message(user_id, result_text, reply_markup=main_menu(), parse_mode='Markdown')
            del user_states[user_id]
            del user_data[user_id]

        return

    # ==== КНОПКИ ГЛАВНОГО МЕНЮ ====
    if text == '📚 Чек-листы':
        bot.send_message(user_id, '📚 Выбери чек-лист:', reply_markup=checklists_menu())
    
    elif text == '🎯 Тесты':
        bot.send_message(user_id, '🎯 Выбери тест:', reply_markup=tests_menu())
    
    elif text == '🌐 Ресурсы':
        bot.send_message(user_id, '🌐 Полезные материалы:', reply_markup=resources_menu())
    
    elif text == '👤 Профиль':
        cmd_profile(message)
    
    elif text == '⚔️ Квесты':
        cmd_quests(message)
    
    elif text == '🎲 Рулетка':
        can_spin, result = spin_wheel(user_id)
        if can_spin:
            # Анимация рулетки
            spin_msg = bot.send_message(user_id, "🎰 Крутим колесо...\n\n🎲🎲🎲")
            import time
            time.sleep(1)
            bot.edit_message_text("🎰 Крутим колесо...\n\n🎯🎯🎯", user_id, spin_msg.message_id)
            time.sleep(1)
            bot.edit_message_text(f"🎰 **РЕЗУЛЬТАТ:**\n\n{result}\n\nПриходи завтра за новым спином!", 
                                user_id, spin_msg.message_id, parse_mode='Markdown')
        else:
            bot.send_message(user_id, result)
    
    elif text == '💡 Идея дня':
        challenge = get_daily_challenge()
        idea = generate_video_idea(user_id)
        
        msg = (f"💡 **КРЕАТИВНЫЙ ЗАРЯД НА СЕГОДНЯ!**\n\n"
               f"🎯 **Челлендж дня:**\n{challenge}\n\n"
               f"🎨 **Идея от ИИ:**\n{idea}\n\n"
               f"Сними и отправь с #challenge!")
        
        bot.send_message(user_id, msg, parse_mode='Markdown')
    
    elif text == '💬 ИИ':
        bot.send_message(user_id, '💬 Напиши свой вопрос, и я отвечу через ИИ!\n\nНапример:\n• Как снять крутой влог?\n• Идеи для видео про школу\n• Как работать со светом?')
    
    else:
        # ИИ отвечает на вопросы
        try:
            # Обновляем счётчик вопросов
            sql("UPDATE user_stats SET ai_questions=ai_questions+1 WHERE user_id=?", (user_id,))
            count_row = sql("SELECT ai_questions FROM user_stats WHERE user_id=?", (user_id,))
            if count_row and count_row[0] >= 20:
                unlock_achievement(user_id, 'ai_master')
            
            # Получаем контекст пользователя
            user_row = sql("""SELECT u.name, u.interests, s.level 
                              FROM users u 
                              JOIN user_stats s ON u.user_id=s.user_id 
                              WHERE u.user_id=?""", (user_id,))
            
            if user_row:
                name, interests, level = user_row
                context = f"Ученик {name}, уровень {level}, интересуется: {interests}."
            else:
                context = "Ученик медиацентра."
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Ты энергичный учитель медиацентра для подростков. {context} Отвечай кратко (до 200 слов), понятно, с эмоджи. Давай конкретные советы по видеосъёмке, монтажу, журналистике, нейросетям. Если вопрос не по теме — мягко направь к нашим урокам. Мотивируй и вдохновляй!"},
                    {"role": "user", "content": text}
                ],
                temperature=0.8,
                max_tokens=300
            )
            
            ai_answer = response.choices[0].message.content
            
            # Начисляем очки за вопрос
            update_user_stats(user_id, 1)
            update_quest_progress(user_id, 'ai_text')
            
            bot.send_message(user_id, f"🤖 {ai_answer}\n\n💡 +1 очко за вопрос!")
        except Exception as e:
            bot.send_message(user_id, f'😅 Упс, ошибка с ИИ: {str(e)}\n\nПопробуй позже или напиши @учитель_бота')

# ============== ЗАПУСК ==============

if __name__ == '__main__':
    print("🚀 Бот запущен!")
    print("📊 Инициализация БД...")
    init_weekly_db()
    init_quests()
    print("✅ Готов к работе!")
    bot.polling(none_stop=True)
