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

# Главное меню с 4 кнопками
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('Чек-лист для написания закадрового текста с ИИ'), KeyboardButton('Чек-лист для съемки репортажа'))
main_menu.add(KeyboardButton('Полезные ресурсы'), KeyboardButton('Курсы aXIS'))

# Состояния для onboard (dict по user_id)
user_states = {}
user_data = {}  # Временное хранение анкеты

# Функция для проверки, в базе ли пользователь
def is_user_in_db(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# Функция для показа меню и финального приветствия
def show_menu_and_greeting(message):
    user_id = message.chat.id
    bot.send_message(user_id, 'Йо, креативный гений! Я твой супер-помощник в медиацентре Марфино. Здесь собрана целая банда помощников: чек-листы для съёмки и текстов, ссылки на полезные ресурсы и курсы. Смотри в меню ниже! ИИ подберёт для тебя правильный ответ с небольшой задержкой, а если не получится — подключит преподавателя. Помни, наша с тобой цель — снимать умопомрачительные видосики, которые собирают море лайков и репостов. Давай творить шедевры! 🎥🔥', reply_markup=main_menu)

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

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text.strip()

    # Обработка onboard по состоянию
    if user_id in user_states:
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

        return  # Чтобы не обрабатывать как обычное сообщение

    # Обработка кнопок меню
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
