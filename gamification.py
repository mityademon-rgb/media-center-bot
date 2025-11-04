"""
Система геймификации: XP, уровни, ачивки
"""
from database import get_user, update_user, load_users, save_users
from config import XP_ATTENDANCE, XP_EVENT, XP_TASK_COMPLETE, XP_TASK_GOOD, XP_TASK_BEST, XP_CHEATSHEET, XP_TEST, LEVELS
from datetime import datetime

# ========== РАБОТА С XP ==========

def add_xp(user_id, amount, reason=""):
    """Добавить XP пользователю"""
    user = get_user(user_id)
    if not user:
        return None
    
    old_xp = user.get('xp', 0)
    new_xp = old_xp + amount
    old_level = get_user_level(old_xp)
    new_level = get_user_level(new_xp)
    
    # Обновляем XP
    update_user(user_id, xp=new_xp)
    
    # Проверяем повышение уровня
    level_up = new_level > old_level
    
    return {
        'old_xp': old_xp,
        'new_xp': new_xp,
        'added': amount,
        'old_level': old_level,
        'new_level': new_level,
        'level_up': level_up,
        'reason': reason
    }

def get_user_level(xp):
    """Получить уровень по XP"""
    level = 1
    for lvl, data in sorted(LEVELS.items(), reverse=True):
        if xp >= data['xp']:
            return lvl
    return level

def get_level_name(level):
    """Получить название уровня"""
    return LEVELS.get(level, {}).get('name', 'Новичок')

def get_xp_to_next_level(xp):
    """Сколько XP нужно до следующего уровня"""
    current_level = get_user_level(xp)
    next_level = current_level + 1
    
    if next_level not in LEVELS:
        return None  # Максимальный уровень
    
    next_level_xp = LEVELS[next_level]['xp']
    return next_level_xp - xp

def get_level_progress(xp):
    """Прогресс в текущем уровне (%)"""
    current_level = get_user_level(xp)
    next_level = current_level + 1
    
    if next_level not in LEVELS:
        return 100  # Максимальный уровень
    
    current_level_xp = LEVELS[current_level]['xp']
    next_level_xp = LEVELS[next_level]['xp']
    
    progress = ((xp - current_level_xp) / (next_level_xp - current_level_xp)) * 100
    return int(progress)

# ========== СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ ==========

def get_user_stats(user_id):
    """Получить статистику пользователя"""
    user = get_user(user_id)
    if not user:
        return None
    
    xp = user.get('xp', 0)
    level = get_user_level(xp)
    level_name = get_level_name(level)
    xp_to_next = get_xp_to_next_level(xp)
    progress = get_level_progress(xp)
    
    return {
        'xp': xp,
        'level': level,
        'level_name': level_name,
        'xp_to_next': xp_to_next,
        'progress': progress,
        'attendance_count': user.get('attendance_count', 0),
        'event_count': user.get('event_count', 0),
        'task_count': user.get('task_count', 0),
        'cheatsheet_count': user.get('cheatsheet_count', 0),
        'test_count': user.get('test_count', 0)
    }

# ========== ПОСЕЩАЕМОСТЬ ==========

def mark_attendance(user_id, date=None):
    """Отметить посещение занятия"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    user = get_user(user_id)
    if not user:
        return None
    
    # Получаем список посещений
    attendance = user.get('attendance', [])
    
    # Проверяем, не отмечено ли уже
    if date in attendance:
        return {'already_marked': True}
    
    # Добавляем дату
    attendance.append(date)
    attendance_count = len(attendance)
    
    # Обновляем данные
    update_user(user_id, 
                attendance=attendance,
                attendance_count=attendance_count)
    
    # Добавляем XP
    xp_result = add_xp(user_id, XP_ATTENDANCE, f"Посещение занятия {date}")
    
    return {
        'success': True,
        'date': date,
        'count': attendance_count,
        'xp_result': xp_result
    }

def mark_event_participation(user_id, event_name):
    """Отметить участие в мероприятии"""
    user = get_user(user_id)
    if not user:
        return None
    
    events = user.get('events', [])
    events.append({
        'name': event_name,
        'date': datetime.now().isoformat()
    })
    event_count = len(events)
    
    update_user(user_id,
                events=events,
                event_count=event_count)
    
    xp_result = add_xp(user_id, XP_EVENT, f"Участие в '{event_name}'")
    
    return {
        'success': True,
        'event': event_name,
        'count': event_count,
        'xp_result': xp_result
    }

# ========== ТВОРЧЕСКИЕ ЗАДАНИЯ ==========

def submit_task(user_id, task_id, file_id):
    """Отправить выполненное задание"""
    user = get_user(user_id)
    if not user:
        return None
    
    submissions = user.get('task_submissions', {})
    submissions[task_id] = {
        'file_id': file_id,
        'submitted_at': datetime.now().isoformat(),
        'status': 'pending',  # pending, checked
        'score': None,
        'comment': None
    }
    
    update_user(user_id, task_submissions=submissions)
    
    # Даём базовый XP за участие
    xp_result = add_xp(user_id, XP_TASK_COMPLETE, f"Выполнение задания")
    
    return {
        'success': True,
        'task_id': task_id,
        'xp_result': xp_result
    }

def rate_task(user_id, task_id, score, comment="", bonus_xp=0):
    """Оценить задание пользователя (админ)"""
    user = get_user(user_id)
    if not user:
        return None
    
    submissions = user.get('task_submissions', {})
    if task_id not in submissions:
        return None
    
    # Обновляем оценку
    submissions[task_id]['status'] = 'checked'
    submissions[task_id]['score'] = score
    submissions[task_id]['comment'] = comment
    submissions[task_id]['checked_at'] = datetime.now().isoformat()
    
    # Считаем общее количество выполненных заданий
    task_count = len([s for s in submissions.values() if s['status'] == 'checked'])
    
    update_user(user_id,
                task_submissions=submissions,
                task_count=task_count)
    
    # Добавляем XP в зависимости от оценки
    xp_amount = 0
    if score == 5:
        xp_amount = XP_TASK_GOOD + bonus_xp
    elif score == 4:
        xp_amount = XP_TASK_GOOD // 2 + bonus_xp
    else:
        xp_amount = bonus_xp
    
    xp_result = None
    if xp_amount > 0:
        xp_result = add_xp(user_id, xp_amount, f"Оценка за задание: {score}/5")
    
    return {
        'success': True,
        'score': score,
        'xp_result': xp_result
    }

# ========== ШПАРГАЛКИ И ТЕСТЫ ==========

def mark_cheatsheet_viewed(user_id, cheatsheet_id):
    """Отметить просмотр шпаргалки"""
    user = get_user(user_id)
    if not user:
        return None
    
    viewed = user.get('cheatsheets_viewed', [])
    
    # Если уже просматривал - не даём XP повторно
    if cheatsheet_id in viewed:
        return {'already_viewed': True}
    
    viewed.append(cheatsheet_id)
    update_user(user_id,
                cheatsheets_viewed=viewed,
                cheatsheet_count=len(viewed))
    
    xp_result = add_xp(user_id, XP_CHEATSHEET, "Просмотр шпаргалки")
    
    return {
        'success': True,
        'xp_result': xp_result
    }

def mark_test_completed(user_id, test_id, score):
    """Отметить прохождение теста"""
    user = get_user(user_id)
    if not user:
        return None
    
    tests = user.get('tests_completed', {})
    tests[test_id] = {
        'score': score,
        'completed_at': datetime.now().isoformat()
    }
    
    update_user(user_id,
                tests_completed=tests,
                test_count=len(tests))
    
    xp_result = add_xp(user_id, XP_TEST, f"Прохождение теста (балл: {score}%)")
    
    return {
        'success': True,
        'xp_result': xp_result
    }

# ========== РЕЙТИНГ ==========

def get_leaderboard(limit=10):
    """Получить топ пользователей по XP"""
    users = load_users()
    
    # Фильтруем только зарегистрированных
    registered_users = [
        u for u in users.values() 
        if u.get('is_registered', False)
    ]
    
    # Сортируем по XP
    sorted_users = sorted(
        registered_users,
        key=lambda x: x.get('xp', 0),
        reverse=True
    )
    
    return sorted_users[:limit]

def get_user_rank(user_id):
    """Получить позицию пользователя в рейтинге"""
    leaderboard = get_leaderboard(limit=999)
    
    for i, user in enumerate(leaderboard, 1):
        if user['user_id'] == user_id:
            return i
    
    return None
