import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os
from openai import OpenAI
import sqlite3
from datetime import datetime

# Токен и OpenAI клиент
bot = telebot.TeleBot(os.environ['TELEGRAM_TOKEN'])
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# Админ ID (ваш Telegram ID)
ADMIN_ID = 397724997

# Подключение к SQLite (база для учеников)
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, name TEXT, experience TEXT, interests TEXT)''')
conn.commit()

# ============== НОВОЕ: таблицы для недельных заданий/очков/квизов ==============
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
        kind TEXT,                -- 'media' | 'quiz' | 'minitest'
        title TEXT,
        description TEXT,
        media_url TEXT,
        deadline TEXT,
        quiz_q TEXT,
        quiz_a TEXT,
        quiz_b TEXT,
        quiz_c TEXT,
        quiz_correct INTEGER      -- 0,1,2
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
        type TEXT,                -- 'media','quiz','minitest'
        PRIMARY KEY(user_id, week_id, type)
    )""")
    sql("""CREATE TABLE IF NOT EXISTS weekly_test_states(
        user_id INTEGER,
        week_id TEXT,
        q_index INTEGER DEFAULT 0,
        score INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, week_id)
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

# Очки по умолчанию
POINTS_MEDIA_FIRST = 5
POINTS_QUIZ_RIGHT = 3
POINTS_MINITEST = {3:5, 2:3, 1:1, 0:0}

# Мини-тест (3 вопроса) — дефолтный набор (можно потом расширять)
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
# ================================================================================

# Чек-листы (как раньше)
checklist_text_ai = """
Нейросети нужно дать четкий и подробный промпт, чтобы она написала хороший закадровый текст. Следуй этому чек-листу:

1. Основная информация о событии
✅ Что это за событие? (концерт, мастер-класс, игра, дискотека и т.д.)
✅ Когда и где оно прошло? (дата, время, название площадки)
✅ Кто организатор? (школа, клуб, администрация, волонтеры)
✅ Кто участники? (ученики, учителя, приглашённые гости)
✅ Какова цель события? (развлечение, обучение, благотворительность)
Пример:
"Это был школьный концерт, который прошел 15 февраля в актовом зале школы №12. Его организовали старшеклассники и учителя музыки. В нем участвовали ученики 5-11 классов. Концерт был посвящен Дню дружбы и направлен на укрепление школьного духа."

2. Описание атмосферы и ключевых моментов
✅ Какая была атмосфера? (веселая, торжественная, дружеская, соревновательная)
✅ Что происходило на сцене или площадке? (какие номера, мастер-классы, игры)
✅ Какие были эмоции у зрителей и участников? (радость, восторг, волнение)
✅ Были ли неожиданные моменты или запоминающиеся эпизоды?
Пример:
"Зрители встретили выступающих громкими аплодисментами. Особенно всем запомнился номер с живой музыкой, где ученики 9 класса исполнили популярную песню на гитаре и фортепиано. А в финале все участники вышли на сцену и спели песню о дружбе."

3. Итоги и важность события
✅ Какое значение имело событие? (вдохновило, научило, сплотило)
✅ Что сказали организаторы или участники? (цитаты, мнения)
✅ Будут ли подобные события в будущем?
Пример:
"По словам организаторов, концерт помог сплотить школьников и подарил всем хорошее настроение. Многие участники признались, что с удовольствием примут участие в следующем концерте, который пройдет весной."

4. Финальная форма промпта
После заполнения всех пунктов составь единый промпт для нейросети.
🔹 Формула промпта:
"Напиши закадровый текст для видеорепортажа о [тип события], которое прошло [дата] в [место]. Организаторы – [кто организовал]. Участвовали [кто был]. Атмосфера была [описание атмосферы]. Произошли такие события: [кратко, что было]. Особенно запомнился момент, когда [интересный момент]. В конце [чем завершилось]. Добавь вывод о важности события и пару фраз от участников."
Пример готового промпта:
"Напиши закадровый текст для видеорепортажа о школьном концерте, который прошел 15 февраля в актовом зале школы №12. Организаторами выступили старшеклассники и учителя. В концерте участвовали ученики 5-11 классов. Атмосфера была радостная и дружеская. На сцене исполняли песни, танцы, сценки. Особенно запомнился момент, когда ученики 9 класса сыграли популярную песню на гитаре и фортепиано. В конце все участники спели финальную песню о дружбе. Концерт помог сплотить школьников. Добавь мнение организаторов и участников о том, как им понравилось."

✅ Теперь нейросеть напишет связный закадровый текст для репортажа! 🎬🎤
"""

checklist_shooting = """
1. Подготовка перед съёмкой
✅ Определите тему репортажа: какое событие освещаете?
✅ Исследуйте информацию о событии, его значимости и участниках.
✅ Составьте план репортажа: какие моменты обязательно должны попасть в кадр?
✅ Подготовьте список вопросов, если планируются интервью.
✅ Проверьте оборудование: заряжены ли камера/телефон, есть ли свободная память?
✅ Возьмите с собой дополнительные аксессуары (штатив, микрофон, пауэрбанк).

2. Съёмка на месте
✅ Снимайте общий план локации, чтобы зрители поняли, где происходит событие.
✅ Записывайте детали: крупные планы важных элементов, эмоции участников.
✅ Интервьюируйте организаторов, гостей, участников.
✅ Проверяйте звук: избегайте шума, старайтесь использовать внешний микрофон.
✅ Записывайте закадровые комментарии во время съемки, чтобы не забыть важные детали.
✅ Держите камеру стабильно, не делайте резких движений.
✅ Делайте несколько дублей важных моментов.
"""

# Полезные ресурсы (ваши ссылки)
resources_text = """
Вот полезные ресурсы для твоего обучения:
- ОСНОВНОЙ КАНАЛ МЕДИАЦЕНТРА МАРФИНО: https://www.youtube.com/@-m50
- ПОЛЕЗНЫЙ БЛОГ: https://www.youtube.com/@%D0%9F%D0%BE%D0%BB%D0%B5%D0%B7%D0%BD%D1%8B%D0%B9%D0%B1%D0%BB%D0%BE%D0%B3
- КУХНЯ И ЛЮДИ: https://www.youtube.com/@%D0%9A%D1%83%D1%85%D0%BD%D1%8F%D0%B8%D0%BB%D1%8E%D0%B4%D0%B8
- СООБЩЕСТВО В ВК: https://vk.com/dkmarfino?from=groups
- СООБЩЕСТВО aXIS: https://vk.com/axisskill?from=groups
Подписывайся и смотри — там куча крутых видосов! 🚀
"""

# Курсы aXIS (ваша ссылка)
courses_text = """
Обязательно зайди на сайт aXIS — это наша онлайн-творческая лаборатория: https://artmediaskill.ru/
Выбери любой курс и получи его бесплатно! Если нужно посоветоваться насчёт курсов или ещё чего, пиши прямо тут — ИИ подберёт или подключит преподавателя.
"""

# Главное меню с кнопками, включая тесты
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('Чек-лист для написания закадрового текста с ИИ'), KeyboardButton('Чек-лист для съемки репортажа'))
main_menu.add(KeyboardButton('Тест по видеосъёмке'), KeyboardButton('Тест по журналистике'))
main_menu.add(KeyboardButton('Полезные ресурсы'), KeyboardButton('Курсы aXIS'))

# Состояния для onboard и тестов (dict по user_id)
user_states = {}
user_data = {}  # Временное хранение анкеты или баллов теста

# Вопросы для теста по видеосъёмке (правильные ответы: B, A, C, B, A)
video_questions = [
    ("Вопрос 1/5: Что лучше использовать для стабильного видео на улице?", ['A: Держать камеру рукой', 'B: Штатив или стабилизатор', 'C: Бежать с камерой'], 'B'),
    ("Вопрос 2/5: Какой план съёмки показывает общее место события?", ['A: Общий план', 'B: Крупный план', 'C: Средний план'], 'A'),
    ("Вопрос 3/5: Что делать с звуком на шумном мероприятии?", ['A: Игнорировать шум', 'B: Использовать встроенный микрофон', 'C: Подключить внешний микрофон'], 'C'),
    ("Вопрос 4/5: Как избежать тряски в видео?", ['A: Снимать на бегу', 'B: Дышать спокойно и держать ровно', 'C: Делать быстрые повороты'], 'B'),
    ("Вопрос 5/5: Зачем проверять оборудование перед съёмкой?", ['A: Чтобы не забыть зарядку и память', 'B: Чтобы сэкономить время', 'C: Чтобы выглядеть круто'], 'A')
]

# Вопросы для теста по журналистике (правильные: C, B, A, C, B)
journalism_questions = [
    ("Вопрос 1/5: Что входит в правило 5W для статьи?", ['A: Who, What, When, Where, Why', 'B: Только Who и What', 'C: Who, What, When, Where, Why'], 'C'),
    ("Вопрос 2/5: Как писать заголовок для репортажа?", ['A: Длинный и скучный', 'B: Краткий и привлекательный', 'C: Без ключевых слов'], 'B'),
    ("Вопрос 3/5: Что такое закадровый текст?", ['A: Голос за кадром, описывающий событие', 'B: Только интервью', 'C: Текст на экране'], 'A'),
    ("Вопрос 4/5: Как подготовиться к интервью?", ['A: Не думать о вопросах', 'B: Задать любые вопросы', 'C: Составить список вопросов заранее'], 'C'),
    ("Вопрос 5/5: Зачем описывать атмосферу в тексте?", ['A: Чтобы заполнить пространство', 'B: Чтобы передать эмоции и вовлечь читателя', 'C: Чтобы сделать текст длиннее'], 'B')
]

# Функция для проверки, в базе ли пользователь
def is_user_in_db(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# Функция для показа меню и финального приветствия
def show_menu_and_greeting(message):
    user_id = message.chat.id
    bot.send_message(user_id, 'Йо, креативный гений! Я твой супер-помощник в медиацентре Марфино. Здесь собрана целая банда помощников: чек-листы для съёмки и текстов, тесты на уровень, ссылки на полезные ресурсы и курсы. Смотри в меню ниже! ИИ подберёт для тебя правильный ответ с небольшой задержкой, а если не получится — подключит преподавателя. Помни, наша с тобой цель — снимать умопомрачительные видосики, которые собирают море лайков и репостов. Давай творить шедевры! 🎥🔥', reply_markup=main_menu)

# ======================== НОВОЕ: команды недели (учитель/ученики) ========================

@bot.message_handler(commands=['week'])
def cmd_week(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Пока нет активного задания недели. Учитель задаёт его командой /setweek")
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
    bot.send_message(message.chat.id, f"👤 Твой счёт за {wid}: {pts} очк.")

@bot.message_handler(commands=['rank'])
def cmd_rank(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Сейчас нет активной недели.")
        return
    rows = top_week(wid, 10)
    if not rows:
        bot.send_message(message.chat.id, f"Пока нет участников за {wid}. Будь первым!")
        return
    medals = ["🥇","🥈","🥉"]
    lines = []
    for i,(uid,pts) in enumerate(rows, start=1):
        mark = medals[i-1] if i<=3 else f"{i}."
        lines.append(f"{mark} ID {uid} — {pts} очк.")
    bot.send_message(message.chat.id, f"🏆 Топ-10 за {wid}:\n" + "\n".join(lines))

# Учитель: задать задание недели (текст, ссылка и т.п.)
@bot.message_handler(commands=['setweek'])
def cmd_setweek(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    text = message.text[len('/setweek'):].strip()
    if not text:
        bot.send_message(message.chat.id,
            "Формат:\n/setweek 2025-W40 | Название | Описание | https://ссылка | до субботы\n"
            "После этого задай тип задания: /kind media или /kind quiz или /kind minitest")
        return
    parts = [p.strip() for p in text.split('|')]
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Нужно минимум 3 части: WEEK_ID | Название | Описание | [Ссылка] | [Дедлайн]")
        return
    week_id = parts[0]
    title = parts[1]
    descr = parts[2]
    link = parts[3] if len(parts)>=4 else ""
    deadline = parts[4] if len(parts)>=5 else ""
    # по умолчанию kind=media (можно сменить /kind ...)
    upsert_task(week_id, 'media', title, descr, link, deadline)
    set_current_week(week_id)
    bot.send_message(message.chat.id, f"✅ Установлено задание недели {week_id}.\nТип: media (можно сменить /kind quiz|minitest)\n\n"
                                      f"{format_task_text(get_task(week_id))}")

@bot.message_handler(commands=['kind'])
def cmd_kind(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    text = message.text.strip().split()
    if len(text)<2 or text[1] not in ('media','quiz','minitest'):
        bot.send_message(message.chat.id, "Используй: /kind media  или  /kind quiz  или  /kind minitest")
        return
    if set_kind(text[1]):
        bot.send_message(message.chat.id, f"✅ Тип задания установлен: {text[1]}")
    else:
        bot.send_message(message.chat.id, "Сначала задай неделю: /setweek ...")

# Учитель: разослать описание недели всем
@bot.message_handler(commands=['sendweek'])
def cmd_sendweek(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет активной недели. /setweek")
        return
    row = get_task(wid)
    if not row:
        bot.send_message(message.chat.id, "Задание недели ещё не настроено.")
        return
    text = "🎮 Новое задание недели!\n\n" + format_task_text(row)
    ids = users_all_ids()
    sent = 0
    for uid in ids:
        try:
            bot.send_message(uid, text)
            sent += 1
        except:
            pass
    bot.send_message(message.chat.id, f"Готово! Отправлено {sent} ученикам.")

# Учитель: начислить очки вручную
@bot.message_handler(commands=['award'])
def cmd_award(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    parts = message.text.strip().split()
    if len(parts)<3:
        bot.send_message(message.chat.id, "Формат: /award <user_id> <очки>")
        return
    try:
        uid = int(parts[1]); pts = int(parts[2])
    except:
        bot.send_message(message.chat.id, "user_id и очки должны быть числами")
        return
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет активной недели. /setweek")
        return
    add_points(uid, wid, pts)
    bot.send_message(message.chat.id, f"✅ Начислено {pts} очков пользователю ID {uid} за {wid}.")

# Учитель: подвести итоги недели (ТОП и победитель)
@bot.message_handler(commands=['summary'])
def cmd_summary(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет активной недели.")
        return
    rows = top_week(wid, 10)
    if not rows:
        bot.send_message(message.chat.id, f"За {wid} никто не участвовал.")
        return
    medals = ["🥇","🥈","🥉"]
    lines = []
    for i,(uid,pts) in enumerate(rows, start=1):
        mark = medals[i-1] if i<=3 else f"{i}."
        lines.append(f"{mark} ID {uid} — {pts} очк.")
    text = f"🎺 ИРА!!! Торжественные итоги недели {wid}\n\n" + "\n".join(lines) + "\n\n⭐ Звезда недели — ID " + str(rows[0][0]) + "!"
    # рассылаем всем
    ids = users_all_ids()
    for uid in ids:
        try:
            bot.send_message(uid, text)
        except:
            pass
    bot.send_message(message.chat.id, "Итоги разосланы. ⭐")

# Квиз недели: задать вопрос (учитель) и пройти (ученики)
@bot.message_handler(commands=['setquiz'])
def cmd_setquiz(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Эта команда только для учителя.")
        return
    # Формат: /setquiz Вопрос | Вариант A | Вариант B | Вариант C | 0
    txt = message.text[len('/setquiz'):].strip()
    parts = [p.strip() for p in txt.split('|')]
    if len(parts) < 5:
        bot.send_message(message.chat.id, "Формат: /setquiz Вопрос | Вариант A | Вариант B | Вариант C | индекс_правильного(0..2)")
        return
    q, a, b, c, idx = parts[0], parts[1], parts[2], parts[3], parts[4]
    try:
        idx = int(idx)
        if idx not in (0,1,2): raise ValueError
    except:
        bot.send_message(message.chat.id, "Последний параметр — число 0..2 (индекс правильного).")
        return
    if not set_quiz(q, a, b, c, idx):
        bot.send_message(message.chat.id, "Сначала задай неделю: /setweek ... и тип: /kind quiz")
        return
    bot.send_message(message.chat.id, "✅ Квиз сохранён. Ученики могут пройти командой /quiz")

@bot.message_handler(commands=['quiz'])
def cmd_quiz(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Сейчас нет активной недели.")
        return
    row = get_task(wid)
    if not row or row[1] != 'quiz' or not row[6]:
        bot.send_message(message.chat.id, "Квиз недели не настроен. Попроси учителя /kind quiz и /setquiz ...")
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
            explanation="Проверь наш урок — там есть подсказки 😉"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"Не удалось отправить квиз: {e}")

# Получаем ответы на квизы и начисляем очки
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
        try:
            bot.send_message(user_id, f"✅ Правильно! +{POINTS_QUIZ_RIGHT} очк. Посмотри /myrank")
        except:
            pass

# Мини-тест недели (3 вопроса) — запуск
@bot.message_handler(commands=['minitest'])
def cmd_minitest(message):
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Сейчас нет активной недели.")
        return
    row = get_task(wid)
    if not row or row[1] != 'minitest':
        bot.send_message(message.chat.id, "На этой неделе мини-тест не активирован. Попроси учителя /kind minitest")
        return
    # сбрасываем прогресс
    sql("INSERT OR REPLACE INTO weekly_test_states(user_id,week_id,q_index,score) VALUES(?,?,0,0)",
        (message.from_user.id, wid))
    q, opts, _ = MINITEST_QUESTIONS[0]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for o in opts: kb.add(KeyboardButton(o))
    bot.send_message(message.chat.id, "📝 Мини-тест (3 вопроса). Вопрос 1/3:\n" + q, reply_markup=kb)

# Приём ответов мини-теста (встраиваем в общий хендлер — он ниже ничего не ломает)

# ========================= ПРИЁМ МЕДИА #challenge (для media-недели) =========================
@bot.message_handler(content_types=['photo','video'])
def handle_media_challenge(message):
    caption = (message.caption or "").lower()
    if "#challenge" not in caption:
        return  # пусть дальше обработается твоим универсальным хендлером
    wid = get_current_week()
    if not wid:
        bot.send_message(message.chat.id, "Нет активной недели. Попроси учителя /setweek")
        return
    row = get_task(wid)
    if not row or row[1] != 'media':
        bot.send_message(message.chat.id, "Сейчас активна неделя не формата «съёмка». Жми /week, чтобы узнать задание.")
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

    # первое участие — очки
    if not already_awarded(message.from_user.id, wid, 'media'):
        add_points(message.from_user.id, wid, POINTS_MEDIA_FIRST)
        mark_awarded(message.from_user.id, wid, 'media')
        bot.send_message(message.chat.id, f"✅ Принято! +{POINTS_MEDIA_FIRST} очк. Посмотри /myrank")
    else:
        bot.send_message(message.chat.id, "✅ Принято! Работа сохранена. Очки за участие уже начислены. /myrank")

# ============================ ТВОЙ ИСХОДНЫЙ КОД НИЖЕ — БЕЗ ИЗМЕНЕНИЙ ============================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if is_user_in_db(user_id):
        show_menu_and_greeting(message)
        return

    bot.send_message(user_id, 'Йо, привет! Я бот медиацентра Марфино. Как тебя зовут? (Напиши реальное имя)')
    user_states[user_id] = 'waiting_name'
    user_data[user_id] = {'name': '', 'experience': '', 'interests': []}

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    user_id = message.chat.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, 'Ты не админ! Эта команда только для организаторов.')
        return

    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.send_message(user_id, 'Напиши текст после /broadcast, например: /broadcast Привет, команда!')
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent_count = 0
    for row in users:
        try:
            bot.send_message(row[0], text)
            sent_count += 1
        except:
            pass  # Если пользователь заблокировал бота — пропустим

    bot.send_message(user_id, f'Рассылка отправлена {sent_count} ученикам!')

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.send_message(message.chat.id, f'Твой Telegram ID: {message.chat.id}')

@bot.message_handler(commands=['listusers'])
def list_users(message):
    user_id = message.chat.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, 'Ты не админ! Эта команда только для организаторов.')
        return

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    if not users:
        bot.send_message(user_id, 'Нет учеников в базе.')
        return

    list_text = "Список учеников:\n"
    for row in users:
        list_text += f"User ID: {row[0]}, Имя: {row[1]}, Опыт: {row[2]}, Интересы: {row[3]}\n\n"
    bot.send_message(user_id, list_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text.strip()

    # ==== Обработка мини-теста (если идёт) ====
    wid = get_current_week()
    if wid:
        st = sql("SELECT q_index,score FROM weekly_test_states WHERE user_id=? AND week_id=?", (user_id, wid))
        if st:
            q_index, score = st
            # ожидаем ответ в формате "A: ..." / "B: ..." / "C: ..."
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
                    bot.send_message(user_id, f"Вопрос {q_index+1}/3:\n{q}", reply_markup=kb)
                    return
                else:
                    # завершили тест
                    sql("DELETE FROM weekly_test_states WHERE user_id=? AND week_id=?", (user_id, wid))
                    if not already_awarded(user_id, wid, 'minitest'):
                        pts = POINTS_MINITEST.get(score, 0)
                        add_points(user_id, wid, pts)
                        mark_awarded(user_id, wid, 'minitest')
                        bot.send_message(user_id, f"✅ Тест завершён: {score}/3. +{pts} очк. /myrank")
                    else:
                        bot.send_message(user_id, f"Тест завершён: {score}/3. Очки уже начислялись ранее. /myrank")
                    return

    # ==== ТВОЙ ОНБОРДИНГ ====
    if user_id in user_states and 'waiting_' in user_states[user_id]:
        state = user_states[user_id]

        if state == 'waiting_name':
            user_data[user_id]['name'] = text
            yes_no_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            yes_no_menu.add(KeyboardButton('Да'), KeyboardButton('Нет'))
            bot.send_message(user_id, f'Круто, {text}! Разрешаешь добавить тебя в нашу базу учеников? Это поможет мне понять, какие материалы тебе нужны, и настроить индивидуальную работу. Без спама, обещаю! 😎', reply_markup=yes_no_menu)
            user_states[user_id] = 'waiting_permission'

        elif state == 'waiting_permission':
            if text.lower() == 'да':
                experience_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                experience_menu.add(KeyboardButton('До 1 года'), KeyboardButton('Больше 1 года'))
                bot.send_message(user_id, 'Отлично! Теперь небольшая анкета — она поможет мне понять, что тебя интересует. Сколько ты посещаешь медиацентр Марфино?', reply_markup=experience_menu)
                user_states[user_id] = 'waiting_experience'
            elif text.lower() == 'нет':
                del user_states[user_id]
                del user_data[user_id]
                bot.send_message(user_id, 'Ок, без проблем! Давай сразу к делу.')
                show_menu_and_greeting(message)
            else:
                bot.send_message(user_id, 'Пожалуйста, выбери "Да" или "Нет".')

        elif state == 'waiting_experience':
            user_data[user_id]['experience'] = text
            interests_menu = ReplyKeyboardMarkup(resize_keyboard=True)
            interests_menu.add(KeyboardButton('Снимать видео'), KeyboardButton('Режиссура'))
            interests_menu.add(KeyboardButton('Журналистика и ведение программ'), KeyboardButton('Блогинг'))
            interests_menu.add(KeyboardButton('Нейросети'), KeyboardButton('Готово'))
            bot.send_message(user_id, 'Что тебя больше интересует? (Можно выбрать несколько, потом нажми "Готово")', reply_markup=interests_menu)
            user_states[user_id] = 'waiting_interests'

        elif state == 'waiting_interests':
            if text == 'Готово':
                interests_str = ', '.join(user_data[user_id]['interests'])
                summary = f"Проверь анкету:\nИмя: {user_data[user_id]['name']}\nОпыт: {user_data[user_id]['experience']}\nИнтересы: {interests_str if interests_str else 'Не указано'}"
                confirm_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                confirm_menu.add(KeyboardButton('Да, верно'), KeyboardButton('Начать заново'))
                bot.send_message(user_id, summary + '\nВсё правильно?', reply_markup=confirm_menu)
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
                bot.send_message(user_id, 'Супер, сохранено! Теперь я могу подстраиваться под тебя.')
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

    # ==== ТВОИ ТЕСТЫ ====
    if text in ['Тест по видеосъёмке', 'Тест по журналистике']:
        if not is_user_in_db(user_id):
            bot.send_message(user_id, 'Сначала зарегистрируйся! Напиши /start и заполни анкету.')
            return

        if text == 'Тест по видеосъёмке':
            user_states[user_id] = 'test_video_q1'
            user_data[user_id] = {'score': 0, 'questions': video_questions}
        else:
            user_states[user_id] = 'test_journalism_q1'
            user_data[user_id] = {'score': 0, 'questions': journalism_questions}

        q, options, _ = user_data[user_id]['questions'][0]
        options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        options_menu.add(*[KeyboardButton(opt) for opt in options])
        bot.send_message(user_id, q, reply_markup=options_menu)
        return

    if user_id in user_states and 'test_' in user_states[user_id]:
        state = user_states[user_id]
        test_type, q_num = state.split('_q')
        q_index = int(q_num) - 1
        questions = user_data[user_id]['questions']
        _, _, correct = questions[q_index]

        answer_letter = text[0]  # A, B или C
        if answer_letter == correct:
            user_data[user_id]['score'] += 1

        if q_index < 4:  # Следующий вопрос
            next_state = f'test_{test_type}_q{q_index + 2}'
            user_states[user_id] = next_state
            q, options, _ = questions[q_index + 1]
            options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            options_menu.add(*[KeyboardButton(opt) for opt in options])
            bot.send_message(user_id, q, reply_markup=options_menu)
        else:  # Конец теста
            score = user_data[user_id]['score']
            if score <= 2:
                verdict = "Ты только начинаешь, но в нашем медиацентре ты всему научишься и станешь профи! 😊 Приходи на уроки!"
            elif score <= 4:
                verdict = "Хорошо, но есть куда расти — приходи на занятия в медиацентр, и всё будет супер!"
            else:
                verdict = "Супер, ты уже мастер! Продолжай практиковать и создавай крутые видео. 🎥"

            bot.send_message(user_id, f'Твой результат: {score}/5. {verdict}', reply_markup=main_menu)
            del user_states[user_id]
            del user_data[user_id]

        return

    # ==== Твои кнопки меню ====
    if text == 'Чек-лист для написания закадрового текста с ИИ':
        bot.send_message(user_id, checklist_text_ai)
    elif text == 'Чек-лист для съемки репортажа':
        bot.send_message(user_id, checklist_shooting)
    elif text == 'Полезные ресурсы':
        bot.send_message(user_id, resources_text)
    elif text == 'Курсы aXIS':
        bot.send_message(user_id, courses_text)
    else:
        # Иначе — ИИ
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты учитель медиацентра для школьников и студентов. Отвечай кратко, напоминая материал из уроков по видеосъёмке, журналистике, написанию текстов, нейросетям. Будь полезным, но не давай опасных советов. Если вопрос не по теме — скажи 'Это не по нашим урокам, спроси о видеосъёмке или нейросетях!'."},
                    {"role": "user", "content": text}
                ]
            )
            ai_answer = response.choices[0].message.content
            bot.send_message(user_id, ai_answer)
        except Exception as e:
            bot.send_message(user_id, f'Извини, ошибка с ИИ: {str(e)}. Попробуй позже или проверь ключ.')

# Запуск polling
if __name__ == '__main__':
    bot.polling(none_stop=True)
