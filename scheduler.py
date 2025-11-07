"""
ПЛАНИРОВЩИК ЗАДАЧ
Автоматические напоминания и рассылки
"""
import schedule
import time
import threading
from datetime import datetime

def start_scheduler(bot):
    """Запустить планировщик в отдельном потоке"""
    
    def run_scheduler():
        """Основной цикл планировщика"""
        
        # Функция ежедневных напоминаний
        def send_daily_reminders():
            """Отправка ежедневных напоминаний"""
            try:
                from database import load_users
                users = load_users()
                
                reminder_text = """🔔 **Доброе утро!**

Не забудь заглянуть в бота:
• 🎯 Проверить новые задания
• 📊 Посмотреть свой прогресс
• 📱 Продолжить обучение

Удачного дня! 🌟"""
                
                count = 0
                for user_id, user_data in users.items():
                    try:
                        bot.send_message(user_id, reminder_text, parse_mode='Markdown')
                        count += 1
                        time.sleep(0.5)  # Задержка между сообщениями
                    except Exception as e:
                        print(f"❌ Не удалось отправить напоминание {user_id}: {e}")
                
                print(f"✅ Отправлено {count} напоминаний")
                
            except Exception as e:
                print(f"❌ Ошибка в send_daily_reminders: {e}")
        
        # Ежедневные напоминания в 9:00
        schedule.every().day.at("09:00").do(send_daily_reminders)
        
        print("⏰ Планировщик запущен!")
        print("• Напоминания: каждый день в 9:00")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверка каждую минуту
    
    # Запускаем в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("✅ Планировщик задач активирован")
