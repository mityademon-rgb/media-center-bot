import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os
from openai import OpenAI
import sqlite3

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

# Чек-листы
checklist_text_ai = """ ... твой текст как был ... """
checklist_shooting = """ ... твой текст как был ... """

# Полезные ресурсы
resources_text = """ ... """
courses_text = """ ... """

# Главное меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('🎬 Чек-лист для написания закадрового текста с ИИ'), KeyboardButton('📹 Чек-лист для съемки репортажа'))
main_menu.add(KeyboardButton('🎯 Тест по видеосъёмке'), KeyboardButton('📰 Тест по журналистике'))
main_menu.add(KeyboardButton('🎥 Урок: Азы операторского искусства'))  # ✅ новая кнопка
main_menu.add(KeyboardButton('🔗 Полезные ресурсы'), KeyboardButton('📚 Курсы aXIS'))

# Состояния
user_states = {}
user_data = {}

# Старые тесты
video_questions = [
    ("Вопрос 1/5: Что лучше использовать для стабильного видео на улице?", ['A: Держать камеру рукой', 'B: Штатив или стабилизатор', 'C: Бежать с камерой'], 'B'),
    ("Вопрос 2/5: Какой план съёмки показывает общее место события?", ['A: Общий план', 'B: Крупный план', 'C: Средний план'], 'A'),
    ("Вопрос 3/5: Что делать с звуком на шумном мероприятии?", ['A: Игнорировать шум', 'B: Использовать встроенный микрофон', 'C: Подключить внешний микрофон'], 'C'),
    ("Вопрос 4/5: Как избежать тряски в видео?", ['A: Снимать на бегу', 'B: Дышать спокойно и держать ровно', 'C: Делать быстрые повороты'], 'B'),
    ("Вопрос 5/5: Зачем проверять оборудование перед съёмкой?", ['A: Чтобы не забыть зарядку и память', 'B: Чтобы сэкономить время', 'C: Чтобы выглядеть круто'], 'A')
]

journalism_questions = [
    ("Вопрос 1/5: Что входит в правило 5W для статьи?", ['A: Who, What, When, Where, Why', 'B: Только Who и What', 'C: Who, What, When, Where, How'], 'A'),
    ("Вопрос 2/5: Как писать заголовок для репортажа?", ['A: Длинный и скучный', 'B: Краткий и привлекательный', 'C: Без ключевых слов'], 'B'),
    ("Вопрос 3/5: Что такое закадровый текст?", ['A: Голос за кадром, описывающий событие', 'B: Только интервью', 'C: Текст на экране'], 'A'),
    ("Вопрос 4/5: Как подготовиться к интервью?", ['A: Не думать о вопросах', 'B: Задать любые вопросы', 'C: Составить список вопросов заранее'], 'C'),
    ("Вопрос 5/5: Зачем описывать атмосферу в тексте?", ['A: Чтобы заполнить пространство', 'B: Чтобы передать эмоции и вовлечь читателя', 'C: Чтобы сделать текст длиннее'], 'B')
]

# ✅ Вопросы мини-теста по операторскому искусству
operator_questions = [
    ("Вопрос 1/3: Что такое 'правило третей'?", 
     ["A: Делим кадр на 3 части и ставим объект на пересечении линий", 
      "B: Нужно снимать только три дубля", 
      "C: Ставим героя строго в центр"], 'A'),

    ("Вопрос 2/3: Какой свет сделает лицо 'страшным'?", 
     ["A: Сбоку", 
      "B: Сверху", 
      "C: Снизу"], 'C'),

    ("Вопрос 3/3: Что лучше — зум или подойти ближе?", 
     ["A: Всегда зум", 
      "B: Подойти ближе", 
      "C: Не важно"], 'B'),
]

# ✅ Слайды урока
lesson_operator = [
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_41_24-300x200.png",
        "text": "📐 Построение кадра — правило третей. 👉 Задание: сними соседа по правилу третей!"
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_43_48-300x200.png",
        "text": "🎬 Крупность плана: общий, средний, крупный. 👉 Задание: сделай три фото одного человека."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_44_29-300x200.png",
        "text": "📷 Угол съёмки: сверху, уровень глаз, снизу. 👉 Задание: попробуй снять игрушку с трёх углов."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_47_04-300x200.png",
        "text": "💡 Свет: сбоку (красиво), сверху (ровно), снизу (страшно). 👉 Задание: подсвети лицо друга фонариком."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_49_33-300x200.png",
        "text": "🎥 Движение камеры: статика, панорама, наезд. 👉 Задание: сними короткое видео с панорамой."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_53_17-300x300.png",
        "text": "✨ Лайфхаки: не зумь — подходи; камера ближе к телу; фон важен; фокус на глаза."
    }
]

# --- Остальной твой код (is_user_in_db, start, broadcast и т.д.) остаётся без изменений ---

def is_user_in_db(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def show_menu_and_greeting(message):
    user_id = message.chat.id
    bot.send_message(user_id, 'Йо, креативный гений! ...', reply_markup=main_menu)

@bot.message_handler(commands=['start'])
def start(message):
    # как у тебя было
    pass

# ... все твои команды broadcast, myid, listusers остаются ...

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text.strip()

    # --- тут твоя логика регистрации и тестов как была ---

    # ✅ Новый урок
    if text == '🎥 Урок: Азы операторского искусства':
        for slide in lesson_operator:
            try:
                bot.send_photo(user_id, slide["img"], caption=slide["text"])
            except:
                bot.send_message(user_id, slide["text"])
        bot.send_message(user_id, "🎯 Урок закончен! Проверим знания — мини-тест.")
        user_states[user_id] = 'test_operator_q1'
        user_data[user_id] = {'score': 0, 'questions': operator_questions}

        q, options, _ = operator_questions[0]
        options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        options_menu.add(*[KeyboardButton(opt) for opt in options])
        bot.send_message(user_id, q, reply_markup=options_menu)
        return

    # ✅ Обработка мини-теста
    if user_id in user_states and 'test_operator' in user_states[user_id]:
        state = user_states[user_id]
        q_num = int(state.split('_q')[1])
        q_index = q_num - 1
        questions = user_data[user_id]['questions']
        _, _, correct = questions[q_index]

        answer_letter = text[0]
        if answer_letter == correct:
            user_data[user_id]['score'] += 1

        if q_index < len(questions) - 1:
            user_states[user_id] = f'test_operator_q{q_index+2}'
            q, options, _ = questions[q_index+1]
            options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            options_menu.add(*[KeyboardButton(opt) for opt in options])
            bot.send_message(user_id, q, reply_markup=options_menu)
        else:
            score = user_data[user_id]['score']
            if score <= 1:
                verdict = "Ты только начинаешь 🎥, но уже круто!"
            elif score == 2:
                verdict = "Отлично! У тебя глаз оператора 👁"
            else:
                verdict = "🔥 Браво! Ты операторский гений!"
            bot.send_message(user_id, f'Результат: {score}/3. {verdict}', reply_markup=main_menu)
            del user_states[user_id]
            del user_data[user_id]
        return

    # --- дальше твоя логика чек-листов, ресурсов и ИИ как была ---

if __name__ == '__main__':
    bot.polling(none_stop=True)
