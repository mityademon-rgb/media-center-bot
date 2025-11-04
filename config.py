"""
Настройки бота
"""
import os

# Токен бота
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8473634161:AAHv_fbBnQ37TboA9LuHCWwgLpjo66daSlA')

# ID админа (твой ID)
ADMIN_ID = 397724997

# Ссылки
LINKS = {
    'site': 'https://promo.artmediaskill.ru/',
    'youtube': 'https://www.youtube.com/@-m50',
    'axis': 'https://artmediaskill.ru'
}

# ========== НАСТРОЙКИ ГЕЙМИФИКАЦИИ ==========

# XP за действия
XP_ATTENDANCE = 50        # За посещение занятия
XP_EVENT = 100            # За участие в мероприятии
XP_TASK_COMPLETE = 50     # За выполнение задания
XP_TASK_GOOD = 100        # За хорошую работу
XP_TASK_BEST = 200        # За лучшую работу
XP_CHEATSHEET = 10        # За просмотр шпаргалки
XP_TEST = 30              # За прохождение теста
XP_BONUS_MONTH = 200      # За идеальную посещаемость месяца

# Уровни (название: минимум XP)
LEVELS = {
    1: {"name": "Новичок", "xp": 0},
    2: {"name": "Ученик", "xp": 200},
    3: {"name": "Оператор", "xp": 500},
    4: {"name": "Профи", "xp": 1000},
    5: {"name": "Мастер", "xp": 2000},
    6: {"name": "Эксперт", "xp": 3500},
    7: {"name": "Легенда", "xp": 5500}
}

# Расписание занятий (дни недели: 0=ПН, 1=ВТ, ..., 6=ВС)
CLASS_DAYS = [1, 3]  # Вторник и Четверг
CLASS_TIME = "16:00"  # Время занятий
