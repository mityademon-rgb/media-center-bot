import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os

# Токен берём из переменной окружения (Railway задаст его)
bot = telebot.TeleBot(os.environ['TELEGRAM_TOKEN'])

# База знаний: разделы и ответы (добавьте свои из уроков)
knowledge_base = {
    'видеосъёмка': {
        'как снять массовое мероприятие на улице': 'Для репортажа: 1. Подготовь оборудование (камера, микрофон, штатив). 2. Выбери точку съёмки с хорошим обзором. 3. Снимай с разных углов: общий план, крупные планы интервью. 4. Учитывай погоду и освещение — используй стабилизатор. 5. Записывай звук отдельно, если шумно. Это из урока по репортажной съёмке!',
        'как стабилизировать видео': 'Используй штатив или гимбал. Держи камеру ровно, дыши спокойно. В монтаже примени стабилизацию в Premiere. Из урока 3.',
        # Добавьте больше: 'вопрос': 'ответ',
    },
    'написание текстов': {
        'как писать заголовок для статьи': 'Заголовок должен быть кратким, информативным и привлекательным. Используй правило 5W (who, what, when, where, why). Пример: "Школьники сняли репортаж о фестивале". Из урока по журналистике.',
        # Добавьте больше
    },
    'нейросети': {
        'как использовать ИИ для генерации идей': 'Введи промпт в ChatGPT или Grok: "Придумай 5 идей для видео о экологии". Уточняй детали для лучших результатов. Из урока по нейросетям.',
        # Добавьте больше
    },
    # Добавьте другие разделы, например 'журналистика': {...}
}

# Главное меню с кнопками
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('Видеосъёмка'), KeyboardButton('Написание текстов'))
main_menu.add(KeyboardButton('Нейросети'), KeyboardButton('Другие разделы'))

current_section = {}  # Для хранения выбранного раздела (простой словарь, для малого количества пользователей)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Я бот медиацентра. Выбери раздел для вопросов:', reply_markup=main_menu)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text.lower() if message.text else ''

    # Если выбрали раздел (по кнопке)
    for section in knowledge_base:
        if text == section.lower():
            current_section[user_id] = section
            bot.send_message(user_id, f'Вы выбрали раздел "{section.capitalize()}". Задай вопрос по теме!')
            return

    # Если вопрос в выбранном разделе
    if user_id in current_section:
        section = current_section[user_id]
        for question, answer in knowledge_base[section].items():
            if any(word in text for word in question.lower().split()):  # Простой поиск по (можно улучшить позже)
                bot.send_message(user_id, answer)
                return
        bot.send_message(user_id, 'Не нашёл точный ответ в этом разделе. Попробуй перефразировать вопрос или вернись в меню (/start).')
    else:
        bot.send_message(user_id, 'Сначала выбери раздел из меню! Напиши /start для начала.')

# Запуск бота (polling — он будет слушать сообщения)
if __name__ == '__main__':
    bot.polling(none_stop=True)
