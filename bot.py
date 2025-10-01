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
checklist_text_ai = """..."""  # оставил твой текст без изменений
checklist_shooting = """...""" # оставил твой текст без изменений

# Полезные ресурсы
resources_text = """..."""
courses_text = """..."""

# Главное меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('🎬 Чек-лист для написания закадрового текста с ИИ'), KeyboardButton('📹 Чек-лист для съемки репортажа'))
main_menu.add(KeyboardButton('🎯 Тест по видеосъёмке'), KeyboardButton('📰 Тест по журналистике'))
main_menu.add(KeyboardButton('🎥 Урок: Азы операторского искусства'))  # ✅ новая кнопка
main_menu.add(KeyboardButton('🔗 Полезные ресурсы'), KeyboardButton('📚 Курсы aXIS'))

# Состояния
user_states = {}
user_data = {}

# Вопросы для тестов (старые оставил как есть)
video_questions = [...]
journalism_questions = [...]

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
        "text": "🎬 Крупность плана: общий, средний, крупный. 👉 Задание: сделай три фото одного человека: общий, средний, крупный."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_44_29-300x200.png",
        "text": "📷 Угол съёмки: сверху, уровень глаз, снизу. 👉 Задание: попробуй снять игрушку с трёх углов."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_47_04-300x200.png",
        "text": "💡 Свет: сбоку (красиво), сверху (ровно), снизу (страшно). 👉 Задание: подсвети лицо друга фонариком с разных сторон."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_49_33-300x200.png",
        "text": "🎥 Движение камеры: статика, панорама, наезд. 👉 Задание: сними короткое видео с панорамой."
    },
    {
        "img": "https://artmediaskill.ru/wp-content/uploads/2025/10/ChatGPT-Image-1-%D0%BE%D0%BA%D1%82.-2025-%D0%B3.-17_53_17-300x300.png",
        "text": "✨ Лайфхаки: не зумь — подходи; камера ближе к телу; фон важен; фокус на глаза. 👉 Задание: сделай фото по этим правилам!"
    }
]

# ===== СТАРЫЕ функции (is_user_in_db, start, broadcast и т.д.) НЕ ТРОГАЕМ =====

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text.strip()

    # --- СТАРЫЕ ОБРАБОТЧИКИ ОСТАВЛЯЕМ БЕЗ ИЗМЕНЕНИЙ ---
    # ...
    # ...

    # ✅ Новый урок
    if text == '🎥 Урок: Азы операторского искусства':
        for slide in lesson_operator:
            try:
                bot.send_photo(user_id, slide["img"], caption=slide["text"])
            except:
                bot.send_message(user_id, slide["text"])
        bot.send_message(user_id, "🎯 Урок закончен! Давай проверим знания — маленький тест.")
        user_states[user_id] = 'test_operator_q1'
        user_data[user_id] = {'score': 0, 'questions': operator_questions}

        # первый вопрос
        q, options, _ = operator_questions[0]
        options_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        options_menu.add(*[KeyboardButton(opt) for opt in options])
        bot.send_message(user_id, q, reply_markup=options_menu)
        return

    # ✅ Проверка мини-теста
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
            verdict = "Ты только начинаешь 🎥, но уже круто!" if score <=1 else "Отлично! У тебя глаз оператора 👁" if score==2 else "🔥 Браво! Ты операторский гений!"
            bot.send_message(user_id, f'Результат: {score}/3. {verdict}', reply_markup=main_menu)
            del user_states[user_id]
            del user_data[user_id]
        return

    # --- ОСТАЛЬНОЕ (чек-листы, тесты, ИИ-ответы) оставляем как у тебя ---
    # ...
    # ...

# Запуск polling
if __name__ == '__main__':
    bot.polling(none_stop=True)
