"""
Интеграция с YandexGPT
"""
import requests
import os

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')

def ask_yandex_gpt(question, context=""):
    """Отправить вопрос в YandexGPT"""
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = """Ты - AI-помощник медиацентра для школьников и студентов. 
Помогаешь с вопросами про:
- Съёмку видео (камеры, свет, композиция)
- Журналистику (интервью, вопросы, подготовка)
- Монтаж и производство контента

Отвечай простым языком, с примерами и эмодзи. Будь дружелюбным!"""
    
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "system",
                "text": system_prompt
            },
            {
                "role": "user",
                "text": question
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        answer = result['result']['alternatives'][0]['message']['text']
        return answer
        
    except Exception as e:
        print(f"Ошибка YandexGPT: {e}")
        return "Извини, не смог обработать запрос. Попробуй позже! 🤖"
