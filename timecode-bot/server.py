"""TIMECODE bot + Mini App. Python standard library only; one process per database."""
import base64
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import random
import secrets
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TOKEN = os.getenv('BOT_TOKEN', '')
BASE = os.getenv('BASE_URL', '').rstrip('/')
GROUP = os.getenv('PUBLIC_CHAT_ID', '')
ADMINS = {int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()}
DB = Path(os.getenv('DATABASE', str(ROOT / 'data/timecode.db'))).resolve()
SECRET = os.getenv('SECRET', '')
JOIN = os.getenv('JOIN_SECRET', '')
AI_KEY = os.getenv('DEEPSEEK_API_KEY', '')
AI_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-flash')
TZ = ZoneInfo('Europe/Moscow')
BOTNAME = ''
AUTH_ATTEMPTS = {}
TIPS = [
 ('Второй подбородок', 'Снимаешь человека снизу? Только что подарил ему второй подбородок. Подними телефон до уровня глаз — герой оценит, даже если не знает почему.'),
 ('Тишина после ответа', 'Не выключай запись сразу после ответа героя. Оставь три секунды тишины: на монтаже скажешь себе спасибо.'),
 ('Свет из окна', 'Окно за спиной человека превращает лицо в загадку. Поверни героя лицом к окну — и освещение уже работает на тебя.'),
 ('Не бойся подойти', 'Если важную деталь плохо видно, сделай шаг ближе. Цифровой зум не заменит ноги оператора.'),
 ('Три плана', 'Снял общий план? Добери средний и крупный. Монтаж из одного красивого кадра часто заканчивается быстрее, чем хочется.'),
 ('Вопрос без да или нет', '«Вам понравилось?» — и интервью закончено. «Какой момент вы запомните?» — и история только началась.'),
 ('Слушай ушами', 'В кадре красиво, а звук похож на холодильник? Перед съёмкой запиши пять секунд тишины и послушай в наушниках.'),
 ('Держи горизонт', 'Море, стены и пол умеют выдавать заваленный кадр. Проверь линии до кнопки записи.'),
 ('Воздух в кадре', 'Герой смотрит вправо? Оставь справа немного места. Пусть взгляд не упирается в край экрана.'),
 ('Снимай действие', '«Человек собирает камеру» интереснее, чем «камера стоит на столе». Ищи глагол, а не предмет.'),
 ('Начни с неожиданного', 'Если сцена скучна первые пять секунд, зритель уже мысленно ушёл. Начни с детали или действия, которое задаёт вопрос.'),
 ('Спроси ещё раз', 'Услышал дежурный ответ? Спроси: «А можно пример?» Часто именно там начинается настоящая история.'),
 ('Не маши камерой', 'Захотелось показать всё одним движением? Остановись. Два спокойных кадра обычно выглядят увереннее одного длинного рывка.'),
 ('Пауза перед началом', 'Нажал запись — подожди две секунды, потом начинай говорить. Монтажёр, даже если это ты сам, будет счастлив.')
]
MISSIONS = [
 ('Один предмет, три плана', 'Сними предмет вокруг себя общим, средним и крупным планом. Выбери лучший и отправь фото боту.', 'photo'),
 ('Первый вопрос', 'Какой вопрос задашь незнакомцу, чтобы ответ был историей, а не словом «да»? Ответь боту одной фразой.', 'text'),
 ('Найди звук', 'Закрой глаза на десять секунд. Какой звук рассказал бы о твоём дне лучше кадра? Пришли боту одно предложение.', 'text'),
 ('Кадр без лиц', 'Сними действие так, чтобы человек оставался за кадром, но зритель понял, что происходит. Пришли фото.', 'photo'),
 ('Заголовок за минуту', 'Посмотри вокруг. Как назвал бы сегодняшнюю короткую новость? Пришли одну строчку.', 'text'),
 ('Ракурс решает', 'Покажи один предмет с необычного ракурса. Пусть остальные угадают, что это. Пришли фото.', 'photo'),
 ('Сцена в трёх словах', 'Опиши момент сегодняшнего дня тремя словами. Больше нельзя: у нас короткий хронометраж.', 'text'),
]

def conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute('pragma busy_timeout=15000')
    c.execute('pragma journal_mode=WAL')
    return c

def init():
    global GROUP
    with conn() as c:
        c.executescript('''
        create table if not exists users(id integer primary key,name text not null,lab text not null default 'kids',role text not null default 'member',enabled integer not null default 1,stage text not null default '',joined integer not null);
        create table if not exists answers(id integer primary key,user_id integer not null,period text not null,day text not null,choice text not null default '',detail text not null default '',published integer not null default 0,unique(user_id,period,day));
        create table if not exists missions(id integer primary key,user_id integer not null,day text not null,kind text not null,answer text not null default '',photo text not null default '',published integer not null default 0,unique(user_id,day));
        create table if not exists lessons(id integer primary key,lab text not null,weekday integer not null,start text not null,title text not null,place text not null default '',enabled integer not null default 1);
        create table if not exists overrides(id integer primary key,day text not null,lab text not null,start text not null,title text not null,place text not null default '',cancelled integer not null default 0);
        create table if not exists sent(slot text not null,day text not null,primary key(slot,day));
        create table if not exists codes(code text primary key,user_id integer not null,expires integer not null);
        create table if not exists progress(user_id integer not null,game text not null,result text not null,day text not null,primary key(user_id,game));
        create table if not exists settings(key text primary key,value text not null);
        ''')
        if not GROUP:
            row=c.execute("select value from settings where key='group_chat'").fetchone()
            if row:GROUP=row['value']

def api(method, data=None):
    if not TOKEN: return {}
    body = json.dumps(data or {}, ensure_ascii=False).encode()
    req = urllib.request.Request('https://api.telegram.org/bot'+TOKEN+'/'+method, body, {'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)
    except Exception as e:
        print('Telegram:', method, str(e)[:180], flush=True)
        return {}

def send(chat, text, keyboard=None):
    payload = {'chat_id':chat, 'text':text, 'parse_mode':'HTML', 'disable_web_page_preview':True}
    if keyboard: payload['reply_markup'] = {'inline_keyboard':keyboard}
    return api('sendMessage', payload)

def edit(chat, message, text):
    return api('editMessageText', {'chat_id':chat,'message_id':message,'text':text,'parse_mode':'HTML'})

def now(): return dt.datetime.now(TZ)
def today(): return now().date().isoformat()
def esc(value): return html.escape(str(value), quote=False)

def ai_digest(kind, facts):
    if not AI_KEY: return None
    prompt = ('Напиши по-русски короткую смешную сводку TIMECODE для школьного медиацентра. '
              'Используй только перечисленные факты, не добавляй людей, обстоятельства или оценки здоровья и учёбы. '
              'Не высмеивай участника. Остроумно, тепло, максимум 650 символов. '
              'Верни только JSON вида {"text":"..."}. Тема: '+kind+'; факты: '+json.dumps(facts,ensure_ascii=False))
    req = urllib.request.Request('https://api.deepseek.com/chat/completions', json.dumps({'model':AI_MODEL,'response_format':{'type':'json_object'},'max_tokens':350,'messages':[{'role':'user','content':prompt}]}).encode(), {'Authorization':'Bearer '+AI_KEY,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=18) as r: data=json.load(r)
        s=json.loads(data['choices'][0]['message']['content']).get('text','').strip()
        return s[:850] or None
    except Exception as e:
        print('DeepSeek:',str(e)[:160],flush=True);return None

def ai_style(source, kind):
    """Rewrite vetted educational copy; never rely on the model for the underlying fact."""
    if not AI_KEY:return None
    system=('Ты редактор подросткового медиацентра TIMECODE. '
            'Пиши живо, весело и коротко. Не меняй фактический смысл исходника, '
            'не добавляй неподтверждённых правил, конкретных людей или грубых шуток. '
            'Ответ только JSON объект вида {"text":"..."}, максимум 280 символов.')
    request='Тип: '+kind+'. Исходный проверенный текст: '+source
    data={'model':AI_MODEL,'response_format':{'type':'json_object'},'max_tokens':170,'messages':[{'role':'system','content':system},{'role':'user','content':request}]}
    req=urllib.request.Request('https://api.deepseek.com/chat/completions',json.dumps(data,ensure_ascii=False).encode(),{'Authorization':'Bearer '+AI_KEY,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=18) as r:result=json.load(r)
        rewrite=json.loads(result['choices'][0]['message']['content'])['text'].strip()
        return rewrite[:280] if rewrite and len(rewrite)<350 else None
    except Exception as e:print('AI style:',str(e)[:160],flush=True);return None

def digest(period):
    with conn() as c:
        rows=c.execute('select u.name,a.choice,a.detail from answers a join users u on u.id=a.user_id where a.day=? and a.period=? and a.published=1 order by a.id',(today(),period)).fetchall()
    if not rows: return
    facts=[{'name':r['name'],'mood':r['choice'],'words':r['detail'][:150]} for r in rows]
    heading='☀️ <b>СВОДКА TIMECODE / УТРО</b>' if period=='am' else '🌙 <b>ТИТРЫ ДНЯ / TIMECODE</b>'
    generated=ai_digest(period,facts)
    if generated:
        # Generated text never gets HTML privileges.
        body=esc(generated)
    else:
        body='\n'.join('• <b>'+esc(f['name'])+'</b> — '+esc(f['words'] or f['mood']) for f in facts[:14])
    send(GROUP,heading+'\n\n'+body)

def tip():
    index=(now().date()-dt.date(2026,1,1)).days % len(TIPS)
    title,body=TIPS[index]
    text=ai_style(body,'короткий полезный лайфхак с лёгкой телевизионной шуткой') or body
    send(GROUP,'⏱ <b>15:00 / ПРИЁМ ДНЯ</b>\n\n<b>'+esc(title)+'</b>\n'+esc(text)+'\n\n<a href="'+esc(BASE)+'">Открыть TIMECODE ↗</a>')

def mission():
    if not BOTNAME:return
    i=(now().date()-dt.date(2026,1,1)).days % len(MISSIONS)
    title,body,_=MISSIONS[i]
    text=ai_style(body,'короткое игровое задание для телефона') or body
    send(GROUP,'🎬 <b>СТРАННОЕ ЗАДАНИЕ</b>\n\n<b>'+esc(title)+'</b>\n'+esc(text),[[{'text':'Ответить боту ↗','url':'https://t.me/'+BOTNAME+'?start=mission'}]])

def weekly():
    weekstart=(now().date()-dt.timedelta(days=6)).isoformat()
    with conn() as c:
        rows=c.execute("select u.name,count(distinct case when a.period='am' then a.day end) morning,count(distinct case when a.period='pm' then a.day end) evening from users u join answers a on u.id=a.user_id and a.day>=? and a.published=1 group by u.id order by morning+evening desc limit 12",(weekstart,)).fetchall()
    if rows:
        lines=['🎞 <b>ТИТРЫ НЕДЕЛИ</b>','']
        lines += ['• '+esc(r['name'])+': утром — '+str(r['morning'])+', вечером — '+str(r['evening'])+'.' for r in rows]
        lines += ['','Это перекличка, не оценки. На следующей неделе будет новый дубль.']
        recap=ai_digest('итоги недели: только числа и доброжелательная шутка',[{'name':r['name'],'morning':r['morning'],'evening':r['evening']} for r in rows])
        if recap:send(GROUP,'🎞 <b>ТИТРЫ НЕДЕЛИ</b>\n\n'+esc(recap))
        else:send(GROUP,'\n'.join(lines))

def class_reminders():
    if not GROUP:return
    t=now(); day=t.date().isoformat()
    with conn() as c:
        overrides=c.execute('select * from overrides where day=?',(day,)).fetchall()
        regular=c.execute('select * from lessons where weekday=? and enabled=1',(t.weekday(),)).fetchall()
    for item in list(overrides)+list(regular):
        lab=item['lab']; override=next((o for o in overrides if o['lab']==lab),None)
        if 'weekday' in item.keys() and override: continue
        event=override if 'weekday' in item.keys() else item
        try: start=dt.datetime.combine(t.date(),dt.time.fromisoformat(event['start']),TZ)
        except ValueError:continue
        if 0 <= (start-t).total_seconds() <= 6000:
            slot='lesson:'+lab+':'+event['start']
            if claim(slot,day):
                label='Kids Lab' if lab=='kids' else 'Media Lab'
                if event['cancelled'] if 'cancelled' in event.keys() else False: continue
                send(GROUP,'🎬 <b>СЕГОДНЯ ЗАНЯТИЕ / '+label+'</b>\n'+esc(event['start'])+' · '+esc(event['title'])+'\n'+esc(event['place'])+'\n\nДмитрий Витальевич ждёт. Камеры зарядить; себя — по возможности тоже.')

def claim(slot,day):
    with conn() as c:
        return c.execute('insert or ignore into sent(slot,day) values (?,?)',(slot,day)).rowcount==1

def run_slot(key,fn):
    if not GROUP and key in ('digest-am','digest-pm','tip','mission','weekly'):return
    if key=='photos-digest' and not GROUP:return
    if claim(key,today()):
        try:fn()
        except Exception as e:print('Slot failed:',key,str(e)[:200],flush=True)

def morning():
    with conn() as c: users=c.execute('select id from users where enabled=1').fetchall()
    for u in users:
        send(u['id'],'☀️ <b>09:00 / УТРЕННЯЯ ПЕРЕКЛИЧКА</b>\nЧто сегодня у тебя происходит? Выбери настроение, потом можешь написать одну фразу.',[[{'text':'🎬 В кадре','callback_data':'mood:am:В кадре'},{'text':'🥱 Сонный оператор','callback_data':'mood:am:Сонный оператор'}],[{'text':'🎞 Пока за кадром','callback_data':'mood:am:Пока за кадром'}]])

def evening():
    with conn() as c: users=c.execute('select id from users where enabled=1').fetchall()
    for u in users:
        send(u['id'],'🌙 <b>19:00 / ВЕЧЕРНЯЯ ПЕРЕКЛИЧКА</b>\nКаким получился сегодняшний дубль? Выбери кнопку и, если хочешь, расскажи одним предложением.',[[{'text':'✨ Получилось','callback_data':'mood:pm:Получилось'},{'text':'😄 Было смешно','callback_data':'mood:pm:Было смешно'}],[{'text':'🔁 Хочу переснять','callback_data':'mood:pm:Хочу переснять'}]])

def scheduler():
    while True:
        try:
            t=now(); clock=t.strftime('%H:%M')
            if clock=='09:00':run_slot('morning',morning)
            if clock=='10:00':run_slot('digest-am',lambda:digest('am'))
            if clock=='15:00':run_slot('tip',tip)
            if clock=='19:00':run_slot('evening',evening)
            if clock=='20:30':run_slot('digest-pm',lambda:digest('pm'))
            if t.weekday() in (0,2,4) and clock=='16:00':run_slot('mission',mission)
            if t.weekday() in (0,2,4) and clock=='20:15':run_slot('photos-digest',photos_digest)
            if t.weekday()==6 and clock=='18:00':run_slot('weekly',weekly)
            class_reminders()
        except Exception as e:print('Scheduler:',str(e)[:200],flush=True)
        time.sleep(20)

def roster(uid,name):
    with conn() as c:
        c.execute("insert into users(id,name,role,joined) values (?,?,?,?) on conflict(id) do update set name=excluded.name",(uid,name[:80],'admin' if uid in ADMINS else 'member',int(time.time())))
        if uid in ADMINS:c.execute("update users set role='admin' where id=?",(uid,))

def allowed(uid):
    with conn() as c:return bool(c.execute('select 1 from users where id=?',(uid,)).fetchone())

def bot_message(msg):
    global GROUP
    chat=msg.get('chat',{}); uid=msg.get('from',{}).get('id');text=msg.get('text','').strip()
    if chat.get('type') in ('group','supergroup') and uid in ADMINS and text.startswith('/connect'):
        GROUP=str(chat['id'])
        with conn() as c:c.execute("insert into settings(key,value) values('group_chat',?) on conflict(key) do update set value=excluded.value",(GROUP,))
        send(GROUP,'🎬 <b>TIMECODE подключён к этому чату.</b> Утренняя сводка выйдет после следующей переклички.')
        return
    if chat.get('type')!='private' or not uid:return
    start=text.partition(' ')[2] if text.startswith('/start') else ''
    if not allowed(uid):
        if uid not in ADMINS and JOIN and start!=JOIN:
            send(uid,'Доступ по приглашению медиацентра. Попроси у преподавателя ссылку TIMECODE.');return
        roster(uid,' '.join(filter(None,[msg.get('from',{}).get('first_name',''),msg.get('from',{}).get('last_name','')])) or 'Участник')
    if text.startswith('/start'):
        if start=='mission':
            with conn() as c:c.execute("update users set stage='mission' where id=?",(uid,))
            send(uid,'🎬 Пришли ответ на сегодняшнее задание: фото или одну короткую фразу. После отправки выберешь, показывать ли её всем.');return
        send(uid,'<b>TIMECODE на связи.</b>\nУтром и вечером здесь перекличка. Игры, уроки и расписание — в приложении.',[[{'text':'Открыть TIMECODE ↗','web_app':{'url':BASE}}]] if BASE else None)
        return
    if text.startswith('/login'):
        code=f'{secrets.randbelow(1000000):06d}'
        with conn() as c:c.execute('insert or replace into codes values (?,?,?)',(code,uid,int(time.time())+300))
        send(uid,'Код для браузера: <b>'+code+'</b>. Действует 5 минут. Никому не пересылай.');return
    if text.startswith('/quiet'):
        with conn() as c:c.execute('update users set enabled=0 where id=?',(uid,))
        send(uid,'Личные переклички выключены. Вернуть: /live');return
    if text.startswith('/live'):
        with conn() as c:c.execute('update users set enabled=1 where id=?',(uid,))
        send(uid,'Личные переклички снова включены.');return
    if text.startswith('/lab'):
        lab=text.partition(' ')[2].strip().lower()
        if lab not in ('kids','media'):send(uid,'Выбери: /lab kids или /lab media');return
        with conn() as c:c.execute('update users set lab=? where id=?',(lab,uid))
        send(uid,'Лаборатория: '+('Kids Lab' if lab=='kids' else 'Media Lab'));return
    if text.startswith('/invite') and uid in ADMINS:
        send(uid,'Ссылка для учеников: https://t.me/'+BOTNAME+'?start='+JOIN if JOIN else 'Сначала настрой JOIN_SECRET.');return
    if text.startswith('/schedule') and uid in ADMINS:
        send(uid,'Добавить занятие: /lesson kids Пн 18:00 | Название | Кабинет\nОтмена или замена на дату: /change kids 2026-10-01 18:00 | Новая тема | Кабинет\nОтмена: /cancel kids 2026-10-01');return
    if uid in ADMINS and text.startswith('/lesson '):
        try:
            left,title,place=(s.strip() for s in text[8:].split('|',2));lab,day,at=left.split();days=['пн','вт','ср','чт','пт','сб','вс'];weekday=days.index(day.lower());assert lab in ('kids','media');dt.time.fromisoformat(at)
            with conn() as c:c.execute('insert into lessons(lab,weekday,start,title,place) values(?,?,?,?,?)',(lab,weekday,at,title,place))
            send(uid,'Занятие добавлено.');return
        except (ValueError,AssertionError):send(uid,'Формат: /lesson kids Пн 18:00 | Тема | Кабинет');return
    if uid in ADMINS and (text.startswith('/change ') or text.startswith('/cancel ')):
        try:
            cancel=text.startswith('/cancel ');part=text.split(' ',1)[1];left,title,place=(s.strip() for s in part.split('|',2)) if not cancel else (part.strip(),'Отмена','');lab,day,*rest=left.split();at=rest[0] if rest else '00:00';dt.date.fromisoformat(day);dt.time.fromisoformat(at);assert lab in ('kids','media')
            with conn() as c:c.execute('insert into overrides(day,lab,start,title,place,cancelled) values(?,?,?,?,?,?)',(day,lab,at,title,place,int(cancel)))
            if GROUP:send(GROUP,'📌 <b>ИЗМЕНЕНИЕ РАСПИСАНИЯ / '+('KIDS LAB' if lab=='kids' else 'MEDIA LAB')+'</b>\n'+esc(day)+' · '+('занятие отменено' if cancel else esc(at)+' · '+esc(title)+' · '+esc(place)))
            send(uid,'Изменение сохранено.');return
        except (ValueError,AssertionError):send(uid,'Формат: /change kids 2026-10-01 18:00 | Новая тема | Кабинет');return
    if uid in ADMINS and text.startswith('/send '):
        send(GROUP,'📢 <b>TIMECODE</b>\n'+esc(text[6:]))
        send(uid,'Опубликовано в общем чате.');return
    with conn() as c: u=c.execute('select stage from users where id=?',(uid,)).fetchone()
    stage=u['stage'] if u else ''
    photo=msg.get('photo',[])[-1]['file_id'] if msg.get('photo') else ''
    if stage=='mission':
        if not photo and not text:send(uid,'Пришли фото или короткую фразу.');return
        kind=MISSIONS[(now().date()-dt.date(2026,1,1)).days % len(MISSIONS)][2]
        if kind=='photo' and not photo:send(uid,'Сегодня фото задание. Отправь один кадр.');return
        with conn() as c:
            c.execute('insert into missions(user_id,day,kind,answer,photo,published) values(?,?,?,?,?,0) on conflict(user_id,day) do update set answer=excluded.answer,photo=excluded.photo,published=0',(uid,today(),kind,(msg.get('caption') or text)[:400],photo))
            c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'Получено! Можно добавить в общую подборку?',[[{'text':'Да, показывайте всем','callback_data':'share:mission:yes'}],[{'text':'Только для себя','callback_data':'share:mission:no'}]])
        return
    if stage.startswith('answer:'):
        period=stage.split(':')[1]
        with conn() as c:
            c.execute('update answers set detail=? where user_id=? and day=? and period=?',(text[:250],uid,today(),period))
            c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'Забрал в блокнот. Опубликовать твой ответ в общей сводке?',[[{'text':'Да, можно','callback_data':'share:'+period+':yes'}],[{'text':'Только мне','callback_data':'share:'+period+':no'}]])
        return
    send(uid,'Открой приложение или подожди утреннюю перекличку. /quiet — выключить личные сообщения; /live — включить. /lab kids или /lab media — выбрать лабораторию.')

def callback(q):
    uid=q.get('from',{}).get('id');data=q.get('data','');msg=q.get('message',{});cid=msg.get('chat',{}).get('id')
    if not uid or not allowed(uid):return
    api('answerCallbackQuery',{'callback_query_id':q['id']})
    if data.startswith('mood:'):
        try:_,period,choice=data.split(':',2)
        except ValueError:return
        if period not in ('am','pm'):return
        with conn() as c:
            c.execute('insert into answers(user_id,period,day,choice) values (?,?,?,?) on conflict(user_id,period,day) do update set choice=excluded.choice,detail="",published=0',(uid,period,today(),choice))
            c.execute('update users set stage=? where id=?',('answer:'+period,uid))
        send(uid,'Записал: '+esc(choice)+'. Одной фразой: что у тебя сегодня происходит? Или нажми «Без подробностей».',[[{'text':'Без подробностей','callback_data':'share:'+period+':choose'}]])
    elif data.startswith('share:'):
        try:_,period,choice=data.split(':',2)
        except ValueError:return
        if period not in ('am','pm','mission'):return
        if choice=='choose':
            send(uid,'Опубликовать в общей сводке только настроение?',[[{'text':'Да','callback_data':'share:'+period+':yes'},{'text':'Нет','callback_data':'share:'+period+':no'}]])
            return
        with conn() as c:
            if period=='mission':c.execute('update missions set published=? where user_id=? and day=?',(int(choice=='yes'),uid,today()))
            else:c.execute('update answers set published=? where user_id=? and day=? and period=?',(int(choice=='yes'),uid,today(),period))
            c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'Принято. '+('Добавлю в общий выпуск.' if choice=='yes' else 'Останется только у тебя.'))

def photos_digest():
    with conn() as c:rows=c.execute('select m.photo,m.answer,u.name from missions m join users u on m.user_id=u.id where m.day=? and m.published=1',(today(),)).fetchall()
    if not rows:return
    pictures=[r for r in rows if r['photo']][:10]
    if len(pictures)>=2:
        media=[{'type':'photo','media':r['photo'],'caption':('🎬 TIMECODE / СЕГОДНЯ В КАДРЕ\n'+r['name']+(' — '+r['answer'] if r['answer'] else ''))[:850]} for r in pictures]
        api('sendMediaGroup',{'chat_id':GROUP,'media':media})
    elif pictures:
        r=pictures[0];api('sendPhoto',{'chat_id':GROUP,'photo':r['photo'],'caption':'🎬 TIMECODE / СЕГОДНЯ В КАДРЕ\n'+r['name']+' — '+r['answer']})
    texts=[r for r in rows if not r['photo']]
    if texts:send(GROUP,'🎬 <b>ОТВЕТЫ ДНЯ</b>\n\n'+'\n'.join('• <b>'+esc(r['name'])+'</b>: '+esc(r['answer'][:200]) for r in texts[:12]))

def polling():
    global BOTNAME
    me=api('getMe'); BOTNAME=(me.get('result') or {}).get('username','')
    offset=0
    while True:
        try:
            data=api('getUpdates',{'offset':offset,'timeout':25,'allowed_updates':['message','callback_query']})
            for update in data.get('result',[]):
                offset=update['update_id']+1
                try:
                    if update.get('message'):bot_message(update['message'])
                    elif update.get('callback_query'):callback(update['callback_query'])
                except Exception as e:print('Update:',str(e)[:200],flush=True)
        except Exception as e:print('Poll:',str(e)[:200],flush=True);time.sleep(3)

def signed(uid):
    payload=str(uid)+'.'+str(int(time.time())+86400*14)
    sig=hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+sig

def user_from_token(raw):
    try:
        uid,expires,sig=raw.split('.')
        payload=uid+'.'+expires
        if int(expires)<time.time() or not hmac.compare_digest(hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest(),sig):return None
        with conn() as c:return c.execute('select * from users where id=?',(int(uid),)).fetchone()
    except (ValueError,AttributeError):return None

def telegram_user(raw):
    try:
        pairs=dict(urllib.parse.parse_qsl(raw,keep_blank_values=True));received=pairs.pop('hash')
        check='\n'.join(k+'='+v for k,v in sorted(pairs.items()))
        key=hmac.new(b'WebAppData',TOKEN.encode(),hashlib.sha256).digest()
        if not hmac.compare_digest(hmac.new(key,check.encode(),hashlib.sha256).hexdigest(),received):return None
        if abs(time.time()-int(pairs['auth_date']))>86400:return None
        return json.loads(pairs['user'])['id']
    except (KeyError,ValueError,TypeError):return None

def code_rate_limit(ip):
    instant=time.time()
    # One six-digit code is valid for five minutes. Slow down online guessing.
    recent=[v for v in AUTH_ATTEMPTS.get(ip,[]) if v>instant-300]
    if len(recent)>=8:return False
    recent.append(instant);AUTH_ATTEMPTS[ip]=recent
    if len(AUTH_ATTEMPTS)>5000:
        for key in list(AUTH_ATTEMPTS)[:2500]:
            if max(AUTH_ATTEMPTS[key],default=0)<instant-300:AUTH_ATTEMPTS.pop(key,None)
    return True

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def out(self,obj,status=200):
        data=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def body(self):
        length=int(self.headers.get('Content-Length','0'))
        if length>100000:return None
        try:return json.loads(self.rfile.read(length))
        except (ValueError,TypeError):return None
    def identity(self):return user_from_token(self.headers.get('Authorization','').removeprefix('Bearer '))
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path=='/health':return self.out({'ok':True,'service':'timecode-bot'})
        if path=='/api/state':
            u=self.identity()
            if not u:return self.out({'error':'Войдите через Telegram'},401)
            with conn() as c:
                lessons=[dict(r) for r in c.execute('select * from lessons where enabled=1 order by weekday,start')]
                changes=[dict(r) for r in c.execute('select * from overrides where day>=? order by day,start',(today(),))]
                progress=[dict(r) for r in c.execute('select * from progress where user_id=?',(u['id'],))]
                latest=[dict(r) for r in c.execute('select day,period,choice,detail from answers where user_id=? order by id desc limit 8',(u['id'],))]
            return self.out({'me':{'id':u['id'],'name':u['name'],'lab':u['lab'],'role':u['role'],'enabled':bool(u['enabled'])},'lessons':lessons,'changes':changes,'progress':progress,'latest':latest,'tip':TIPS[(now().date()-dt.date(2026,1,1)).days%len(TIPS)],'mission':MISSIONS[(now().date()-dt.date(2026,1,1)).days%len(MISSIONS)],'date':today(),'bot':BOTNAME})
        if path not in ('/','/app.js','/style.css'):return self.out({'error':'Не найдено'},404)
        file=ROOT/'static'/('index.html' if path=='/' else path[1:]);blob=file.read_bytes()
        self.send_response(200);self.send_header('Content-Type',{'html':'text/html','js':'text/javascript','css':'text/css'}[file.suffix[1:]]+'; charset=utf-8');self.send_header('Content-Length',str(len(blob)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(blob)
    def do_POST(self):
        path=urllib.parse.urlsplit(self.path).path;p=self.body()
        if p is None:return self.out({'error':'Неверный запрос'},400)
        if path=='/api/auth':
            uid=telegram_user(p.get('initData','')) if p.get('initData') else None
            if uid is None and p.get('code'):
                if not code_rate_limit(self.client_address[0]):return self.out({'error':'Слишком много попыток. Подождите 5 минут.'},429)
                with conn() as c:
                    row=c.execute('select user_id from codes where code=? and expires>?',(str(p['code']),int(time.time()))).fetchone()
                    if row:uid=row['user_id'];c.execute('delete from codes where code=?',(str(p['code']),))
            if uid and allowed(uid):return self.out({'token':signed(uid)})
            return self.out({'error':'Нет доступа. Откройте приглашение TIMECODE.'},403)
        u=self.identity()
        if not u:return self.out({'error':'Сначала войдите'},401)
        if path=='/api/profile':
            lab=p.get('lab')
            if lab not in ('kids','media'):return self.out({'error':'Выберите лабораторию'},400)
            with conn() as c:c.execute('update users set lab=?,enabled=? where id=?',(lab,int(bool(p.get('enabled',True))),u['id']))
            return self.out({'ok':True})
        if path=='/api/game':
            if p.get('game') not in ('cinema','shot','interview','differences'):return self.out({'error':'Неизвестная игра'},400)
            answer=str(p.get('result',''))[:120]
            with conn() as c:c.execute('insert into progress values(?,?,?,?) on conflict(user_id,game) do update set result=excluded.result,day=excluded.day',(u['id'],p['game'],answer,today()))
            return self.out({'ok':True})
        if path=='/api/lesson' and u['role']=='admin':
            try:
                lab=str(p['lab']);day=int(p['weekday']);at=str(p['start']);title=str(p['title']).strip();place=str(p.get('place','')).strip()
                assert lab in ('kids','media') and 0<=day<=6 and 1<=len(title)<=90
                dt.time.fromisoformat(at)
                with conn() as c:c.execute('insert into lessons(lab,weekday,start,title,place) values(?,?,?,?,?)',(lab,day,at,title,place[:80]))
                return self.out({'ok':True})
            except (KeyError,ValueError,AssertionError):return self.out({'error':'Проверьте дату и поля'},400)
        if path=='/api/override' and u['role']=='admin':
            try:
                lab=str(p['lab']);day=str(p['day']);at=str(p['start']);title=str(p.get('title','')).strip() or 'Занятие';place=str(p.get('place',''))[:80];cancel=int(bool(p.get('cancelled')))
                assert lab in ('kids','media');dt.date.fromisoformat(day);dt.time.fromisoformat(at)
                with conn() as c:c.execute('insert into overrides(day,lab,start,title,place,cancelled) values(?,?,?,?,?,?)',(day,lab,at,title[:90],place,cancel))
                if GROUP:send(GROUP,'📌 <b>ИЗМЕНЕНИЕ РАСПИСАНИЯ / '+('KIDS LAB' if lab=='kids' else 'MEDIA LAB')+'</b>\n'+esc(day)+' · '+('занятие отменено' if cancel else esc(at)+' · '+esc(title[:90])+' · '+esc(place)))
                return self.out({'ok':True})
            except (KeyError,ValueError,AssertionError):return self.out({'error':'Проверьте дату и поля'},400)
        return self.out({'error':'Нет доступа'},403)

if __name__=='__main__':
    if not SECRET or len(SECRET)<32:raise SystemExit('Set SECRET to at least 32 random characters')
    init()
    if TOKEN:
        if not BASE.startswith('https://'):raise SystemExit('BASE_URL must be HTTPS for Telegram Mini Apps')
        if len(JOIN)<20 or not ADMINS:raise SystemExit('Set JOIN_SECRET (20+ characters) and ADMIN_IDS before enabling bot')
        threading.Thread(target=polling,daemon=True).start()
        threading.Thread(target=scheduler,daemon=True).start()
    print('TIMECODE listening on 127.0.0.1:'+os.getenv('PORT','8097'),flush=True)
    ThreadingHTTPServer(('127.0.0.1',int(os.getenv('PORT','8097'))),Handler).serve_forever()
