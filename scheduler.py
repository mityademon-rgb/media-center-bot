"""
Планировщик задач (напоминания)
"""
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_users_waiting_qr
from registration import send_qr_reminder

scheduler = BackgroundScheduler()

def check_qr_reminders(bot):
    """Проверить, кому нужно отправить напоминание о QR-коде"""
    users_waiting = get_users_waiting_qr()
    
    for user_data in users_waiting:
        try:
            send_qr_reminder(bot, user_data)
            print(f"✅ Напоминание отправлено пользователю {user_data['user_id']}")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания: {e}")

def start_scheduler(bot):
    """Запустить планировщик"""
    # Проверка каждые 30 минут
    scheduler.add_job(
        check_qr_reminders,
        'interval',
        minutes=30,
        args=[bot]
    )
    
    scheduler.start()
    print("✅ Планировщик напоминаний запущен!")
