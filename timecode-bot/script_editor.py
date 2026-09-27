"""Private screenplay submissions and constructive AI feedback."""
import base64
import binascii
import io
import json
import re
import secrets
import subprocess
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_FILE = 2_000_000
EXTENSIONS = {'.txt', '.fountain', '.docx', '.pdf'}


def install(c):
    c.execute('''create table if not exists script_reviews(
        id integer primary key, user_id integer not null, name text not null,
        filename text not null, stored_name text not null, created integer not null,
        feedback text not null default '', admin_sent integer not null default 0)''')


def extract(name, blob):
    ext = Path(name).suffix.lower()
    if ext not in EXTENSIONS:
        raise ValueError('Подойдёт сценарий в PDF, DOCX, TXT или Fountain.')
    if not blob or len(blob) > MAX_FILE:
        raise ValueError('Файл пустой или больше 2 МБ.')
    if ext in ('.txt', '.fountain'):
        text = blob.decode('utf-8-sig', errors='replace')
    elif ext == '.pdf':
        if not blob.startswith(b'%PDF-'):
            raise ValueError('Файл не похож на PDF.')
        result = subprocess.run(['pdftotext', '-layout', '-', '-'], input=blob,
                                capture_output=True, timeout=12)
        if result.returncode:
            raise ValueError('Не удалось прочитать PDF. Пришли текстовый PDF или DOCX.')
        text = result.stdout.decode('utf-8', errors='replace')
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                names = z.namelist()
                if len(names)>200 or sum(i.file_size for i in z.infolist())>12_000_000:
                    raise ValueError('DOCX слишком большой.')
                root = ET.fromstring(z.read('word/document.xml'))
                ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                text = '\n'.join(''.join(t.text or '' for t in p.iter(ns+'t'))
                                 for p in root.iter(ns+'p'))
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            raise ValueError('Не удалось прочитать DOCX.')
    text = re.sub(r'\n{4,}', '\n\n\n', text).strip()
    if len(text) < 120:
        raise ValueError('В сценарии слишком мало текста для разбора. Если PDF состоит из картинок, пришли DOCX или TXT.')
    return text


def deliver(path, filename, user, number, admins, token):
    if not token or not admins:
        return False
    caption = f'Сценарий #{number} от {user["name"]} (ID {user["id"]}). Оригинал для чтения преподавателем.'[:900]
    success = True
    for admin in admins:
        try:
            result = subprocess.run(['curl', '-4', '-fsS', '--connect-timeout', '8', '--max-time', '35',
                '-F', 'chat_id='+str(admin), '-F', 'caption='+caption,
                '-F', 'document=@'+str(path)+';filename='+filename,
                'https://api.telegram.org/bot'+token+'/sendDocument'],
                capture_output=True, timeout=40)
            success = success and result.returncode == 0 and json.loads(result.stdout).get('ok') is True
        except (OSError, ValueError, subprocess.TimeoutExpired):
            success = False
    return success


def submit(c, data, user, db_path, admins, token, ai_json):
    raw_name = str(data.get('filename', ''))
    filename = Path(raw_name.replace('\\', '/')).name[:110]
    if not filename or Path(filename).suffix.lower() not in EXTENSIONS:
        raise ValueError('Выбери PDF, DOCX, TXT или Fountain.')
    try:
        blob = base64.b64decode(data.get('content_base64', ''), validate=True)
    except (ValueError, binascii.Error, TypeError):
        raise ValueError('Не удалось прочитать файл.')
    text = extract(filename, blob)
    folder = db_path.parent / 'student_scripts'
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder.chmod(0o700)
    stored = secrets.token_hex(20) + Path(filename).suffix.lower()
    path = folder / stored
    with path.open('xb') as stream:
        stream.write(blob)
    path.chmod(0o600)
    cursor = c.execute('insert into script_reviews(user_id,name,filename,stored_name,created) values(?,?,?,?,?)',
                       (user['id'], user['name'][:80], filename, stored, int(time.time())))
    number = cursor.lastrowid
    c.commit()
    delivered = deliver(path, filename, user, number, admins, token)
    c.execute('update script_reviews set admin_sent=? where id=?', (int(delivered), number))
    c.commit()
    system = ('Ты редактор сценариев школьного медиацентра TIMECODE. Пиши подростку на равных, конкретно и бережно. '
              'Назови удачные детали сюжета, две или три реальные слабости с примерами из текста и предложи выполнимые исправления. '
              'Не выдумывай сцены, которых нет, не переписывай весь сценарий и не цитируй длинные куски. '
              'Лёгкая ирония возможна, если она не направлена на автора. Ответ на русском, три поля good, improve, fix, каждое до 700 символов.')
    response = ai_json(system, 'Сценарий «'+filename+'»:\n'+text[:32000]+
                       ('\n[Дальнейший текст не помещается в один разбор.]' if len(text)>32000 else '')+
                       '\nВерни JSON с полями good, improve, fix.', 780)
    feedback = {key: str((response or {}).get(key, '')).strip()[:1100]
                for key in ('good', 'improve', 'fix')}
    if not all(feedback.values()):
        feedback = {'good': 'Сценарий загружен, его уже может прочитать преподаватель.',
                    'improve': 'Кими сейчас не смог сделать честный разбор текста.',
                    'fix': 'Попробуй запросить разбор позднее или обсуди сценарий с преподавателем.'}
    c.execute('update script_reviews set feedback=? where id=?',
              (json.dumps(feedback, ensure_ascii=False), number))
    c.commit()
    return {'id': number, 'feedback': feedback, 'teacher_delivered': delivered}


def retry(c, db_path, admins, token):
    rows = c.execute('select * from script_reviews where admin_sent=0 order by id limit 10').fetchall()
    for row in rows:
        path = db_path.parent / 'student_scripts' / row['stored_name']
        user = {'name': row['name'], 'id': row['user_id']}
        if path.is_file() and deliver(path, row['filename'], user, row['id'], admins, token):
            c.execute('update script_reviews set admin_sent=1 where id=?', (row['id'],))
