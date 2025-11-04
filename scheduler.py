"""
Планировщик задач (напоминания)
"""
import schedule
import time
import threading
from datetime import datetime, timedelta
from database import load_users, get_user
from registration import send_qr_reminder

def check_qr_reminders(bot):
    """Проверить, кому нужно отправить напоминание о QR-коде"""
    users = load_users()
    now = datetime.now()
    
    for user_data in users.values():
        # Проверяем только тех, кто на 5 шаге и не отправлял QR
        if user_data.get('registration_step') != 5:
            continue
        
        if user_data.get('qr_code'):
            continue
        
        # Проверяем, не отправляли ли уже напоминание
        if user_data.get('qr_reminder_sent'):
            continue
        
        # Проверяем, прошло ли 24 часа с момента запроса
        qr_requested = user_data.get('qr_requested_at')
        if not qr_requested:
            continue
        
        try:
            requested_time = datetime.fromisoformat(qr_requested)
            if (now - requested_time) >= timedelta(hours=24):
                send_qr_reminder(bot, user_data)
        except:
            continue

def check_event_reminders(bot):
    """Проверить и отправить напоминания о мероприятиях"""
    try:
        from notifications import send_event_reminders
        sent = send_event_reminders(bot)
        if sent > 0:
            print(f"✅ Отправлено {sent} напоминаний о мероприятиях")
    except Exception as e:
        print(f"❌ Ошибка отправки напоминаний: {e}")

def send_morning_messages(bot):
    """Отправить утренние сообщения"""
    try:
        from notifications import send_morning_schedule
        sent = send_morning_schedule(bot)
        if sent > 0:
            print(f"✅ Отправлено {sent} утренних сообщений")
    except Exception as e:
        print(f"❌ Ошибка отправки утренних сообщений: {e}")

def send_weekly_preview(bot):
    """Отправить анонс недели"""
    try:
        from notifications import send_week_preview
        sent = send_week_preview(bot)
        if sent > 0:
            print(f"✅ Отправлено {sent} анонсов недели")
    except Exception as e:
        print(f"❌ Ошибка отправки анонсов недели: {e}")

def run_scheduler(bot):
    """Запуск планировщика в отдельном потоке"""
    
    # Проверка напоминаний о QR-коде каждые 6 часов
    schedule.every(6).hours.do(lambda: check_qr_reminders(bot))
    
    # Проверка напоминаний о мероприятиях каждый час
    schedule.every().hour.do(lambda: check_event_reminders(bot))
    
    # Утреннее расписание в 9:00
    schedule.every().day.at("09:00").do(lambda: send_morning_messages(bot))
    
    # Анонс недели в воскресенье в 19:00
    schedule.every().sunday.at("19:00").do(lambda: send_weekly_preview(bot))
    
    print("✅ Планировщик задач запущен!")
    print("   • Напоминания о QR: каждые 6 часов")
    print("   • Напоминания о событиях: каждый час")
    print("   • Утреннее расписание: 9:00")
    print("   • Анонс недели: ВС 19:00")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверка каждую минуту

def start_scheduler(bot):
    """Запустить планировщик в фоновом потоке"""
    scheduler_thread = threading.Thread(target=run_scheduler, args=(bot,), daemon=True)
    scheduler_thread.start()
