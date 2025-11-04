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
        from schedule_module import send_daily_reminders
        
        # Ежедневные напоминания в 9:00
        schedule.every().day.at("09:00").do(lambda: send_daily_reminders(bot))
        
        print("⏰ Планировщик запущен!")
        print("• Напоминания: каждый день в 9:00")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверка каждую минуту
    
    # Запускаем в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("✅ Планировщик задач активирован")
