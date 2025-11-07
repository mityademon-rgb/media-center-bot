"""
ПЛАНИРОВЩИК ЗАДАЧ
Автоматические напоминания и рассылки
"""
import threading
import time

def start_scheduler(bot):
    """Запустить планировщик в отдельном потоке"""
    
    def run_scheduler():
        """Основной цикл планировщика"""
        print("⏰ Планировщик запущен (без автонапоминаний)")
        
        # Пока просто держим поток активным
        while True:
            time.sleep(3600)  # Проверка каждый час
    
    # Запускаем в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("✅ Планировщик задач активирован")
