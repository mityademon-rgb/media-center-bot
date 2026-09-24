"""Reviewed, data-only TIMECODE quest campaigns. No executable AI output."""
import datetime as dt
import json
import sqlite3
import time
import urllib.request


def install(c):
    c.executescript('''
    create table if not exists quest_drafts (
        id integer primary key, lab text not null, status text not null,
        content text not null, created integer not null, published_day text not null default '',
        reviewer integer not null default 0);
    create table if not exists quest_runs (
        quest_id integer not null, user_id integer not null, choices text not null default '[]',
        updated integer not null, primary key(quest_id,user_id));
    ''')


def verify(value, lab):
    if not isinstance(value, dict) or lab not in ('kids', 'media'):
        raise ValueError('Неверная лаборатория или сценарий')
    for name, cap in (('title', 75), ('hook', 330)):
        if not isinstance(value.get(name), str) or not 12 <= len(value[name]) <= cap:
            raise ValueError('Нет названия или завязки')
    chapters = value.get('chapters')
    if not isinstance(chapters, list) or len(chapters) != 4:
        raise ValueError('Требуются четыре законченные главы')
    for chapter in chapters:
        if not isinstance(chapter, dict):
            raise ValueError('Глава отсутствует')
        for name, low, high in (('title', 5, 90), ('scene', 70, 650),
                                ('alternate', 40, 450), ('question', 15, 180)):
            if not isinstance(chapter.get(name), str) or not low <= len(chapter[name]) <= high:
                raise ValueError('Сцена не укладывается в экран: ' + name)
        if chapter.get('visual') not in ('studio', 'camera', 'archive', 'moon', 'city'):
            raise ValueError('Неизвестная декорация')
        options = chapter.get('choices')
        if not isinstance(options, list) or len(options) != 3:
            raise ValueError('Нужны три разных решения в каждой главе')
        labels = []
        for choice in options:
            if not isinstance(choice, dict):
                raise ValueError('Пустое решение')
            for name, low, high in (('label', 12, 130), ('effect', 35, 290)):
                if not isinstance(choice.get(name), str) or not low <= len(choice[name]) <= high:
                    raise ValueError('Выбор без последствия: ' + name)
            if choice.get('track') not in ('evidence', 'trust', 'craft'):
                raise ValueError('Нет параметра, на который влияет выбор')
            if choice.get('points') not in (-1, 0, 1):
                raise ValueError('Баллы выбора вне допустимого диапазона')
            labels.append(choice['label'])
        if len(set(labels)) != 3:
            raise ValueError('Повторяются варианты решения')
    endings = value.get('endings')
    if not isinstance(endings, dict) or set(endings) != {'evidence', 'trust', 'craft'}:
        raise ValueError('Нужны три финала')
    for text in endings.values():
        if not isinstance(text, str) or not 100 <= len(text) <= 600:
            raise ValueError('Финал слишком короткий или длинный')
    return value


def generate(lab, theme, api_key, model, params):
    if not api_key:
        raise ValueError('Kimi API не подключён')
    theme = (theme or 'Пропавший финальный кадр перед премьерой').strip()[:180]
    age = '12–13 лет, Kids Lab' if lab == 'kids' else '14–17 лет, Media Lab'
    system = ('Ты сценарист интерактивной игры TIMECODE для ' + age + '. '
              'Создай ОДИН цельный игровой сезон, а не тест на знания. Четыре короткие главы по дням, '
              'три содержательных выбора в каждой главе, видимые последствия и три разных финала. '
              'Игрок — участник редакции и влияет на увиденные улики, отношения и историю фильма. '
              'Следующая глава alternate должна менять смысл сцены при сумме evidence >= 1. '
              'Три направления выбора: evidence, trust, craft; points целое -1, 0 или 1. '
              'В третьем выборе последней главы нужно определить смысл финала. '
              'Никаких заданий с незнакомцами, травлей, угрозами и опасными действиями. '
              'Сюжет короткий, с характером и юмором, без школьного учебника. '
              'Иллюстрации не рисуй: visual — один из studio, camera, archive, moon, city. '
              'Ответ строго JSON: title, hook, chapters (ровно четыре объекта с полями '
              'title, scene, alternate, visual, question, choices (ровно три объекта с label, '
              'effect, track, points)), endings (evidence, trust, craft — три полноценных финала).')
    prompt = 'Тема: ' + theme + '. Каждый выбор меняет события следующего эпизода. Развилки должны быть правдоподобными.'
    payload = {'model': model, 'response_format': {'type': 'json_object'},
               'max_tokens': 5000, 'messages': [{'role': 'system', 'content': system},
                                                {'role': 'user', 'content': prompt}], **params}
    req = urllib.request.Request('https://api.moonshot.ai/v1/chat/completions',
                                 json.dumps(payload, ensure_ascii=False).encode(),
                                 {'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=95) as response:
        result = json.load(response)
    return verify(json.loads(result['choices'][0]['message']['content']), lab)


def save_draft(c, lab, data):
    return c.execute('insert into quest_drafts(lab,status,content,created) values (?,?,?,?)',
                     (lab, 'draft', json.dumps(data, ensure_ascii=False), int(time.time()))).lastrowid


def state(c, uid, lab, is_admin, today):
    rows = c.execute("select * from quest_drafts where status='published' and lab=? "
                     "or (?=1 and status='draft') order by id desc limit 12", (lab, int(is_admin))).fetchall()
    result = []
    for row in rows:
        game = json.loads(row['content'])
        progress = c.execute('select choices from quest_runs where quest_id=? and user_id=?',
                             (row['id'], uid)).fetchone()
        chosen = json.loads(progress['choices']) if progress else []
        release_day = row['published_day'] or today
        if row['status'] == 'draft':
            unlocked = 4
        else:
            unlocked = max(0, min(4, (dt.date.fromisoformat(today) -
                                      dt.date.fromisoformat(release_day)).days + 1))
        chapter_index = min(len(chosen), 3)
        scores = {'evidence': 0, 'trust': 0, 'craft': 0}
        for i, choice_id in enumerate(chosen):
            option = game['chapters'][i]['choices'][choice_id]
            scores[option['track']] += option['points']
        last = game['chapters'][len(chosen) - 1]['choices'][chosen[-1]]['effect'] if chosen else ''
        ending = game['endings'][max(scores, key=lambda key: (scores[key], key))] if len(chosen) == 4 else ''
        result.append({'id': row['id'], 'lab': row['lab'], 'status': row['status'],
                       'title': game['title'], 'hook': game['hook'], 'chapter': len(chosen),
                       'unlocked': unlocked, 'last_effect': last, 'ending': ending,
                       'scene': (game['chapters'][chapter_index] if len(chosen) < 4 else None),
                       'alternative': scores['evidence'] >= 1, 'preview': row['status'] == 'draft'})
    return result


def choose(c, quest_id, uid, lab, index, today):
    row = c.execute('select * from quest_drafts where id=? and lab=? and status=?',
                    (quest_id, lab, 'published')).fetchone()
    if not row:
        raise ValueError('Этот квест пока не опубликован для твоей лаборатории')
    unlocked = min(4, max(0, (dt.date.fromisoformat(today) -
                              dt.date.fromisoformat(row['published_day'])).days + 1))
    game = json.loads(row['content'])
    run = c.execute('select choices from quest_runs where quest_id=? and user_id=?',
                    (quest_id, uid)).fetchone()
    chosen = json.loads(run['choices']) if run else []
    if len(chosen) >= unlocked or len(chosen) >= 4:
        raise ValueError('Следующая серия ещё не вышла')
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < 3:
        raise ValueError('Выбери один из трёх ходов')
    chosen.append(index)
    c.execute('insert into quest_runs(quest_id,user_id,choices,updated) values(?,?,?,?) '
              'on conflict(quest_id,user_id) do update set choices=excluded.choices,updated=excluded.updated',
              (quest_id, uid, json.dumps(chosen), int(time.time())))
    return game['chapters'][len(chosen) - 1]['choices'][index]['effect']
