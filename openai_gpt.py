"""
Интеграция с OpenAI GPT
"""
import openai
import os

# API ключ из переменных окружения
openai.api_key = os.getenv('OPENAI_API_KEY')

def ask_gpt(question, context="", model="gpt-3.5-turbo"):
    """Отправить вопрос в OpenAI GPT"""
    
    system_prompt = """Ты - AI-помощник медиацентра для школьников и студентов. 
Помогаешь с вопросами про:
- Съёмку видео (камеры, свет, композиция)
- Журналистику (интервью, вопросы, подготовка)
- Монтаж и производство контента

Отвечай простым языком, с примерами и эмодзи. Будь дружелюбным, мотивирующим и креативным!
Если вопрос не по теме медиацентра - вежливо направь разговор в нужное русло."""
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        return answer
        
    except openai.error.RateLimitError:
        return "⏱️ Слишком много запросов! Подожди немного и попробуй снова."
        
    except openai.error.AuthenticationError:
        return "🔑 Ошибка авторизации. Проверь API-ключ!"
        
    except openai.error.InvalidRequestError as e:
        print(f"Неверный запрос: {e}")
        return "❌ Не удалось обработать запрос. Попробуй переформулировать!"
        
    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        return "🤖 Что-то пошло не так. Попробуй позже!"


def ask_gpt_with_context(question, chat_history=[], model="gpt-3.5-turbo"):
    """Задать вопрос с учётом истории диалога"""
    
    system_prompt = """Ты - AI-помощник медиацентра для школьников и студентов. 
Помогаешь с вопросами про съёмку, журналистику и создание контента.
Отвечай простым языком с примерами и эмодзи. Учитывай контекст предыдущих вопросов."""
    
    # Формируем сообщения с историей
    messages = [{"role": "system", "content": system_prompt}]
    
    # Добавляем последние 5 сообщений из истории
    for msg in chat_history[-5:]:
        messages.append({"role": "user", "content": msg['question']})
        messages.append({"role": "assistant", "content": msg['answer']})
    
    # Добавляем текущий вопрос
    messages.append({"role": "user", "content": question})
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        return answer
        
    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        return ask_gpt(question, model=model)  # Fallback без контекста


def get_quick_answer(question, model="gpt-3.5-turbo"):
    """Быстрый короткий ответ (до 300 токенов)"""
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "Ты - помощник медиацентра. Отвечай кратко и по делу."},
                {"role": "user", "content": question}
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return "❌ Не удалось получить ответ"
