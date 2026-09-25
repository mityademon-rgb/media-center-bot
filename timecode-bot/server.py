"""TIMECODE bot + Mini App. Python standard library only; one process per database."""
import datetime as dt
import base64
import hashlib
import hmac
import html
import re
import json
import os
import secrets
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo
import quest_engine as quests

ROOT = Path(__file__).resolve().parent
TOKEN = os.getenv('BOT_TOKEN', '')
BASE = os.getenv('BASE_URL', '').rstrip('/')
GROUP = os.getenv('PUBLIC_CHAT_ID', '')
ADMINS = {int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()}
DB = Path(os.getenv('DATABASE', str(ROOT / 'data/timecode.db'))).resolve()
SECRET = os.getenv('SECRET', '')
JOIN = os.getenv('JOIN_SECRET', '')
AI_KEY = os.getenv('MOONSHOT_API_KEY', '')
AI_MODEL = os.getenv('KIMI_MODEL', 'kimi-k2.6')
VISION_MODEL = os.getenv('KIMI_VISION_MODEL', AI_MODEL)
AI_API = 'https://api.moonshot.ai/v1'
TZ = ZoneInfo('Europe/Moscow')
BOTNAME = ''
AUTH_ATTEMPTS = {}
SOURCE_SETS = (
    ('blog.frame.io','studiobinder.com','nofilmschool.com','bhphotovideo.com'),
    ('youtube.com','aputure.com','studiobinder.com','blog.frame.io'),
    ('nofilmschool.com','blog.frame.io','poynter.org','studiobinder.com'),
)
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
MISSION_FORMATS = (
    ('photo', 'Найди интересную деталь вокруг себя и покажи её одним кадром.', 'Сними один кадр, в котором деталь меняет смысл всей сцены.'),
    ('text', 'Придумай вопрос, на который нельзя ответить одним словом.', 'Придумай один вопрос, который раскроет героя без подсказки в ответе.'),
    ('text', 'История начинается с пустой студии или с руки, которая включает камеру? Выбери начало и объясни одной фразой.', 'Начать репортаж с пустой студии или с крупного плана кнопки REC? Выбери начало и объясни одной фразой.'),
    ('photo', 'Покажи действие одним кадром без лица человека.', 'Покажи действие через деталь, не снимая чужих лиц.'),
    ('text', 'Придумай смешное название для обычного предмета в кадре.', 'Придумай заголовок, который превратит обычную сцену в историю.'),
    ('text', 'Заметь необычный звук и назови его одной фразой.', 'Предложи, каким звуком открыть сцену, чтобы сразу возник вопрос.'),
)

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
        create table if not exists evening_checkins(user_id integer not null,day text not null,mood text not null default '',highlight text not null default '',satisfied text not null default '',visible integer not null default 0,step text not null default '',primary key(user_id,day));
        create table if not exists morning_checkins(user_id integer not null,day text not null,sleep text not null default '',mood text not null default '',important text not null default '',photo text not null default '',visible integer not null default 0,step text not null default '',primary key(user_id,day));
        create table if not exists missions(id integer primary key,user_id integer not null,day text not null,kind text not null,answer text not null default '',photo text not null default '',published integer not null default 0,unique(user_id,day));
        create table if not exists lessons(id integer primary key,lab text not null,weekday integer not null,start text not null,title text not null,place text not null default '',enabled integer not null default 1);
        create table if not exists overrides(id integer primary key,day text not null,lab text not null,start text not null,title text not null,place text not null default '',cancelled integer not null default 0);
        create table if not exists sent(slot text not null,day text not null,primary key(slot,day));
        create table if not exists codes(code text primary key,user_id integer not null,expires integer not null);
        create table if not exists progress(user_id integer not null,game text not null,result text not null,day text not null,primary key(user_id,game));
        create table if not exists settings(key text primary key,value text not null);
        create table if not exists questions(id integer primary key,user_id integer not null,body text not null,created integer not null,answered integer not null default 0);
        create table if not exists question_receipts(admin_id integer not null,message_id integer not null,question_id integer not null,primary key(admin_id,message_id));
        create table if not exists daily_content(day text not null,kind text not null,title text not null,body text not null,mode text not null default 'text',source text not null default '',primary key(day,kind));
        ''')
        quests.install(c)
        columns={row['name'] for row in c.execute('pragma table_info(daily_content)')}
        for name in ('body_kids','body_media'):
            if name not in columns:c.execute('alter table daily_content add column '+name+" text not null default ''")
        if 'photo' not in {row['name'] for row in c.execute('pragma table_info(evening_checkins)')}:
            c.execute("alter table evening_checkins add column photo text not null default ''")
        if 'comment' not in {row['name'] for row in c.execute('pragma table_info(missions)')}:
            c.execute("alter table missions add column comment text not null default ''")
        if not GROUP:
            row=c.execute("select value from settings where key='group_chat'").fetchone()
            if row:GROUP=row['value']

def api(method, data=None):
    if not TOKEN: return {}
    try:
        timeout=35 if method=='getUpdates' else 18
        response=subprocess.run(['curl','-4','-fsS','--connect-timeout','8',
                                 '--max-time',str(timeout),'-H','Content-Type: application/json',
                                 '--data-binary','@-',
                                 'https://api.telegram.org/bot'+TOKEN+'/'+method],
                                input=json.dumps(data or {},ensure_ascii=False),text=True,
                                capture_output=True,timeout=timeout+4)
        if response.returncode==0:return json.loads(response.stdout)
        print('Telegram:',method,'transport code',response.returncode,flush=True)
    except Exception as error:
        print('Telegram:',method,'request failed',type(error).__name__,flush=True)
        return {}
    return {}

def send(chat, text, keyboard=None):
    payload = {'chat_id':chat, 'text':text, 'parse_mode':'HTML', 'disable_web_page_preview':True}
    if keyboard: payload['reply_markup'] = {'inline_keyboard':keyboard}
    return api('sendMessage', payload)

def send_attachment(chat, msg, caption):
    """Publish a media file from Telegram by file_id; no server download."""
    types=(('photo','sendPhoto','photo'),('document','sendDocument','document'),('video','sendVideo','video'))
    for key,method,field in types:
        value=msg.get(key)
        if not value:continue
        file_id=value[-1]['file_id'] if isinstance(value,list) else value['file_id']
        return api(method,{'chat_id':chat,field:file_id,'caption':caption[:950]})
    return {}

def ask_admins(uid,body):
    with conn() as c:
        question_id=c.execute('insert into questions(user_id,body,created) values (?,?,?)',(uid,body[:2000],int(time.time()))).lastrowid
        row=c.execute('select name from users where id=?',(uid,)).fetchone()
    name=row['name'] if row else 'Ученик'
    delivered=False
    for admin_id in ADMINS:
        response=send(admin_id,'❓ <b>ВОПРОС #'+str(question_id)+'</b> от '+esc(name)+'\n\n'+esc(body[:2000])+'\n\nОтветь прямо на это сообщение или нажми кнопку.',[[{'text':'Ответить ученику ↗','callback_data':'admin:question:'+str(question_id)}]])
        mid=(response.get('result') or {}).get('message_id')
        if mid:
            with conn() as c:c.execute('insert or replace into question_receipts values (?,?,?)',(admin_id,mid,question_id))
            delivered=True
    return delivered

def answer_question(admin_id,question_id,text='',attachment=None):
    with conn() as c:row=c.execute('select * from questions where id=?',(question_id,)).fetchone()
    if not row or row['answered']:
        send(admin_id,'Вопрос не найден или на него уже ответили.');return
    intro='✉️ <b>ОТВЕТ TIMECODE НА ТВОЙ ВОПРОС</b>\n\n'
    result=send_attachment(row['user_id'],attachment,'Ответ TIMECODE: '+text) if attachment else send(row['user_id'],intro+esc(text))
    if not result.get('ok'):
        send(admin_id,'Не удалось доставить ответ ученику. Вопрос сохранён.');return
    with conn() as c:c.execute('update questions set answered=1 where id=? and answered=0',(question_id,))
    send(admin_id,'Ответ на вопрос #'+str(question_id)+' доставлен.')

def edit(chat, message, text):
    return api('editMessageText', {'chat_id':chat,'message_id':message,'text':text,'parse_mode':'HTML'})

def now(): return dt.datetime.now(TZ)
def today(): return now().date().isoformat()
def esc(value): return html.escape(str(value), quote=False)

def kimi_params():
    return {'thinking':{'type':'disabled'}} if AI_MODEL=='kimi-k2.6' else {'reasoning_effort':'low'} if AI_MODEL=='kimi-k3' else {}

def kimi_request(path,payload,timeout=24):
    response=subprocess.run(['curl','-4','-fsS','--connect-timeout','8',
                             '--max-time',str(timeout),'-H','Content-Type: application/json',
                             '-H','Authorization: Bearer '+AI_KEY,'--data-binary','@-',
                             AI_API+path],input=json.dumps(payload,ensure_ascii=False),
                            text=True,capture_output=True,timeout=timeout+4)
    if response.returncode:raise ValueError('Kimi transport code '+str(response.returncode))
    return json.loads(response.stdout)

def ai_digest(kind, facts):
    if not AI_KEY: return None
    prompt = ('Напиши по-русски короткую смешную сводку TIMECODE для школьного медиацентра. '
              'Используй только перечисленные факты, не добавляй людей, обстоятельства или оценки здоровья и учёбы. '
              'Не высмеивай участника. Остроумно, тепло, максимум 650 символов. '
              'Верни только JSON вида {"text":"..."}. Тема: '+kind+'; факты: '+json.dumps(facts,ensure_ascii=False))
    try:
        data=kimi_request('/chat/completions',{'model':AI_MODEL,'response_format':{'type':'json_object'},'max_tokens':350,'messages':[{'role':'user','content':prompt}],**kimi_params()})
        s=json.loads(data['choices'][0]['message']['content']).get('text','').strip()
        return s[:850] or None
    except Exception as e:
        print('Kimi:',str(e)[:160],flush=True);return None

def ai_json(system,request,max_tokens=250):
    if not AI_KEY:return None
    data={'model':AI_MODEL,'response_format':{'type':'json_object'},'max_tokens':max_tokens,'messages':[{'role':'system','content':system+' Ответ только JSON.'},{'role':'user','content':request}],**kimi_params()}
    try:
        result=kimi_request('/chat/completions',data)
        obj=json.loads(result['choices'][0]['message']['content'])
        return obj if isinstance(obj,dict) else None
    except Exception as e:print('AI research:',str(e)[:160],flush=True);return None

def photo_comment(file_id):
    """View a Telegram-compressed photo with Kimi; return a playful caption or ''."""
    if not AI_KEY or not TOKEN:return ''
    file=(api('getFile',{'file_id':file_id}).get('result') or {})
    path=file.get('file_path','')
    if not re.fullmatch(r'photos/[A-Za-z0-9_-]+\.jpe?g',path) or file.get('file_size',0)>4_000_000:return ''
    try:
        fetched=subprocess.run(['curl','-4','-fsS','--connect-timeout','8','--max-time','20','--max-filesize','4000000',
                                'https://api.telegram.org/file/bot'+TOKEN+'/'+path],capture_output=True,timeout=23)
        if fetched.returncode or not 0<len(fetched.stdout)<=4_000_000:return ''
        content=[{'type':'text','text':('Ты остроумный редактор школьного медиацентра TIMECODE. Посмотри на РЕАЛЬНОЕ фото ученика и придумай одну смешную подпись на русском до 120 символов. '
                                         'Шути о предметах, композиции и неожиданном сюжете кадра, не о внешности, здоровье, личной жизни или способностях людей. '
                                         'Не выдумывай детали вне кадра, не пытайся узнать личность или место. Если непонятно, что изображено, дай нейтральную, но остроумную подпись. Верни одну строку без кавычек.')},
                 {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(fetched.stdout).decode('ascii')}}]
        data=kimi_request('/chat/completions',{'model':VISION_MODEL,'max_tokens':110,'messages':[{'role':'user','content':content}],
                                               **({'thinking':{'type':'disabled'}} if VISION_MODEL.startswith('kimi-k2.') else {})},timeout=30)
        result=str(data['choices'][0]['message']['content']).strip().strip('"«»').splitlines()[0]
        return result[:170] if 8<=len(result)<=220 else ''
    except Exception as error:
        print('Kimi photo:',type(error).__name__,flush=True)
        return ''

def industry_search(query,sites):
    """Kimi Search Pro returns passages and URLs from selected film-industry sites."""
    if not AI_KEY:return None
    payload={'text_query':query[:140],'limit':5,'timeout_seconds':18,'sites':list(sites)[:5]}
    try:
        results=kimi_request('/tools/search_pro',payload,timeout=28).get('search_results',[])
        for page in results:
            url=str(page.get('url',''))
            parsed=urllib.parse.urlsplit(url)
            host=(parsed.hostname or '').lower()
            if parsed.scheme!='https' or not any(host==site or host.endswith('.'+site) for site in sites):continue
            passages=' '.join(str(x.get('text','')) for x in page.get('chunks',[])[:3])
            excerpt=re.sub('<[^>]+>','',passages or str(page.get('snippet','')))
            excerpt=html.unescape(excerpt).strip()
            if len(excerpt)<100:continue
            return {'title':str(page.get('title',''))[:150],'snippet':excerpt[:1300],'url':url}
    except Exception as e:print('Industry search:',str(e)[:160],flush=True)
    return None

def fallback_content(kind):
    index=(now().date()-dt.date(2026,1,1)).days
    if kind=='tip':
        title,body=TIPS[index%len(TIPS)]
        return {'title':title,'body':body,'mode':'text','source':''}
    mode,kids,media=MISSION_FORMATS[index%len(MISSION_FORMATS)]
    return {'title':'МИКРОЗАДАНИЕ / '+('КАДР' if mode=='photo' else 'РЕШЕНИЕ'),'body':kids,'body_kids':kids,'body_media':media,'mode':mode,'source':''}

def creative_enabled():
    with conn() as c:
        row=c.execute("select value from settings where key='creative_ai'").fetchone()
    return row is None or row['value']=='on'

def make_daily(kind):
    default=fallback_content(kind)
    if not AI_KEY or not creative_enabled():return default
    if kind=='tip':
        previous=[]
        with conn() as c:previous=[r['title'] for r in c.execute("select title from daily_content where kind='tip' order by day desc limit 10")]
        sites=SOURCE_SETS[(now().date()-dt.date(2026,1,1)).days%len(SOURCE_SETS)]
        query=ai_json('Ты редактор молодежного медиацентра. Придумай конкретную англоязычную поисковую фразу для необычного ПРАКТИЧЕСКОГО совета о съёмке на телефон, монтаже, репортаже или интервью. Ищи в заданных профессиональных медиа и у киноавторов. Не повторяй недавние темы. JSON {"query":"..."}.',json.dumps({'previous':previous,'sites':sites,'day':today()},ensure_ascii=False),120)
        topic=str((query or {}).get('query','filmmaking practical camera sound lighting tip'))[:110]
        found=industry_search(topic,sites)
        if not found:return default
        drafted=ai_json('Ты остроумный автор TIMECODE. По фрагменту материала киноавтора или профильного медиа придумай короткий полезный совет для подростка с телефоном. Только то, что подтверждено во фрагменте; никаких вымышленных реплик автора или универсальных технических законов. Один неожиданный ход и лёгкая ирония, максимум 250 символов. Верни JSON {"title":"до 45 символов","body":"..."}.',json.dumps(found,ensure_ascii=False),290)
        title=str((drafted or {}).get('title','')).strip();body=str((drafted or {}).get('body','')).strip()
        if 3<=len(title)<=55 and 40<=len(body)<=320:return {'title':title,'body':body,'mode':'text','source':found['url']}
        return default
    previous=[]
    with conn() as c:previous=[dict(r) for r in c.execute("select title,mode from daily_content where kind='mission' order by day desc limit 10")]
    planned=MISSION_FORMATS[(now().date()-dt.date(2026,1,1)).days%len(MISSION_FORMATS)]
    drafted=ai_json('Ты игровой редактор TIMECODE, лаборатории креативных медиа. Придумай ОДНО новое забавное задание для смартфона на 1–3 минуты, с двумя возрастными формулировками одной и той же идеи: Kids Lab 12–13 лет — проще и игровее; Media Lab 14–17 лет — чуть сложнее, с редакторским или операторским выбором. Ровно заданный формат ответа: photo — одно фото, text — одна короткая фраза. Не повторяй недавние идеи. Не проси идти к незнакомцам, загружать личные сведения, снимать людей без согласия или делать опасное. Если предлагаешь выбор, перечисли оба конкретных варианта прямо в задании: ученик не видит никаких приложенных кадров или файлов. Никаких длинных объяснений. JSON {"title":"до 45 символов","kids":"до 180 символов","media":"до 180 символов","mode":"photo или text"}.',json.dumps({'previous':previous,'day':today(),'mode':planned[0],'direction_kids':planned[1],'direction_media':planned[2]},ensure_ascii=False),350)
    title=str((drafted or {}).get('title','')).strip();kids=str((drafted or {}).get('kids','')).strip();media=str((drafted or {}).get('media','')).strip();mode=str((drafted or {}).get('mode',''))
    if any(re.search(r'из двух вариантов|из этих кадров|посмотри на (?:эти|два) кадра', phrase, re.I) for phrase in (kids,media)):return default
    if 3<=len(title)<=55 and 25<=len(kids)<=200 and 25<=len(media)<=200 and mode==planned[0]:return {'title':title,'body':kids,'body_kids':kids,'body_media':media,'mode':mode,'source':''}
    return default

def daily_content(kind,generate=False):
    day=today()
    with conn() as c:row=c.execute('select title,body,body_kids,body_media,mode,source from daily_content where day=? and kind=?',(day,kind)).fetchone()
    if row:return {k:row[k] for k in (('title','body','body_kids','body_media','mode','source') if kind=='mission' else ('title','body','mode','source'))}
    if not generate:return fallback_content(kind)
    value=make_daily(kind)
    with conn() as c:
        c.execute('insert or ignore into daily_content(day,kind,title,body,mode,source,body_kids,body_media) values(?,?,?,?,?,?,?,?)',(day,kind,value['title'],value['body'],value['mode'],value['source'],value.get('body_kids',''),value.get('body_media','')))
        row=c.execute('select title,body,body_kids,body_media,mode,source from daily_content where day=? and kind=?',(day,kind)).fetchone()
    return {k:row[k] for k in (('title','body','body_kids','body_media','mode','source') if kind=='mission' else ('title','body','mode','source'))}

def digest(period):
    if period=='pm':return evening_digest()
    with conn() as c:
        rows=c.execute("select u.name,u.lab,m.sleep,m.mood,m.important from morning_checkins m join users u on u.id=m.user_id where m.day=? and m.step='done' and m.mood!='' order by u.name",(today(),)).fetchall()
    sections=[]
    for lab,label in (('kids','KIDS LAB'),('media','MEDIA LAB')):
        people=[r for r in rows if r['lab']==lab]
        if not people:sections.append('<b>'+label+'</b> · Пока в эфире тихо. Ждём следующего выпуска.');continue
        facts=[{'name':r['name'],'sleep':r['sleep'],'mood':r['mood'],'plans':r['important'][:140]} for r in people]
        generated=ai_digest('утро '+label,facts) if people else None
        fallback='\n'.join('• <b>'+esc(r['name'])+'</b>: '+esc(r['mood'].lower())+', '+esc(r['sleep'].lower())+(('; '+esc(r['important'][:130])) if r['important'] else '') for r in people[:12])
        sections.append('<b>'+label+'</b> · На связи '+str(len(people))+'\n'+(esc(generated) if generated else fallback))
    send(GROUP,'☀️ <b>10:00 / УТРЕННЯЯ СВОДКА TIMECODE</b>\n\n'+'\n\n'.join(sections))

def evening_digest():
    with conn() as c:
        rows=c.execute("select u.name,u.lab,e.mood,e.highlight,e.satisfied from evening_checkins e join users u on u.id=e.user_id where e.day=? and e.step='done' and e.mood!='' order by u.name",(today(),)).fetchall()
    sections=[]
    for lab,label in (('kids','KIDS LAB'),('media','MEDIA LAB')):
        people=[r for r in rows if r['lab']==lab]
        if not people:sections.append('<b>'+label+'</b> · Сегодня без публичных ответов.');continue
        counts={k:sum(r['mood']==k for r in people) for k in ('Хороший','Обычный','Сложный')}
        part='<b>'+label+'</b> · На связи '+str(len(people))+'. Хороший день: '+str(counts['Хороший'])+', обычный: '+str(counts['Обычный'])+', непростой: '+str(counts['Сложный'])+'. Довольны днём: '+str(sum(r['satisfied']=='Да' for r in people))+'.'
        highlights=['• <b>'+esc(r['name'])+'</b>: '+esc(r['highlight'][:140]) for r in people if r['highlight'] and r['highlight']!='Не было']
        sections.append(part+('\n'+'\n'.join(highlights[:10]) if highlights else ''))
    send(GROUP,'🌙 <b>20:30 / КАК ПРОШЁЛ ДЕНЬ</b>\n\n'+'\n\n'.join(sections))

def tip():
    item=daily_content('tip',True)
    source='\n<a href="'+html.escape(item['source'],quote=True)+'">Откуда идея ↗</a>' if item['source'] else ''
    send(GROUP,'⏱ <b>15:00 / ПРИЁМ ДНЯ</b>\n\n<b>'+esc(item['title'])+'</b>\n'+esc(item['body'])+source,[[{'text':'Открыть лайфхак в TIMECODE ↗','url':BASE+'/?view=tip'}]])

def quest_next_episodes():
    with conn() as c:
        rows=c.execute("select id,lab,content,published_day from quest_drafts where status='published' and published_day between ? and ?",((now().date()-dt.timedelta(days=3)).isoformat(),today())).fetchall()
        chats={r['key']:r['value'] for r in c.execute("select key,value from settings where key like 'quest_chat_%'")}
    for row in rows:
        chapter=(now().date()-dt.date.fromisoformat(row['published_day'])).days+1
        if not 2<=chapter<=4 or not chats.get('quest_chat_'+row['lab']):continue
        story=json.loads(row['content'])
        if claim('quest:'+str(row['id'])+':'+str(chapter),today()):
            send(chats['quest_chat_'+row['lab']],'🎞 <b>'+esc(story['title'])+'</b>\nОткрыта серия '+str(chapter)+'/4: '+esc(story['chapters'][chapter-1]['title'])+'. То, что ты сделал раньше, изменит следующую сцену.',[[{'text':'Продолжить ↗','url':BASE+'/?view=quests&id='+str(row['id'])}]])

def mission():
    if not BOTNAME:return
    item=daily_content('mission',True)
    kids=item['body_kids'] or item['body'];media=item['body_media'] or item['body']
    send(GROUP,'🎬 <b>СТРАННОЕ ЗАДАНИЕ</b>\n\n<b>'+esc(item['title'])+'</b>\n\n<b>Kids Lab:</b> '+esc(kids)+'\n<b>Media Lab:</b> '+esc(media),[[{'text':'Ответить боту ↗','url':'https://t.me/'+BOTNAME+'?start=mission'}]])

def instant_photo():
    if not BOTNAME:return
    message='📸 <b>МГНОВЕННОЕ ФОТО</b>\nСфоткай то, что прямо сейчас перед тобой. Один кадр, без подготовки. Присылай до 20:00 — вечером соберём общую подборку. Если в кадре люди, спроси их согласия.'
    send(GROUP,message,[[{'text':'Отправить кадр боту ↗','url':'https://t.me/'+BOTNAME+'?start=instant'}]])
    with conn() as c:users=c.execute('select id from users where enabled=1').fetchall()
    for u in users:
        with conn() as c:c.execute("update users set stage='instant' where id=? and stage=''",(u['id'],))
        send(u['id'],message+'\nПришли фото прямо сюда, если хочешь участвовать.')

def weekly():
    weekstart=(now().date()-dt.timedelta(days=6)).isoformat()
    with conn() as c:
        rows=c.execute("select u.name,(select count(*) from morning_checkins m where m.user_id=u.id and m.day>=? and m.step='done') morning,(select count(*) from evening_checkins e where e.user_id=u.id and e.day>=? and e.step='done') evening from users u order by morning+evening desc limit 12",(weekstart,weekstart)).fetchall()
        rows=[r for r in rows if r['morning']+r['evening']>0]
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
        send(u['id'],'☀️ <b>07:30 / ДОБРОЕ УТРО!</b>\nКак спалось, как дела и что сегодня важного? Три быстрых ответа. Если не хочется — можно просто не отвечать. Собираю до 09:00.',[[{'text':'😌 Выспался','callback_data':'morning:sleep:Выспался'},{'text':'😐 Так себе','callback_data':'morning:sleep:Так себе'}],[{'text':'🥱 Мало спал','callback_data':'morning:sleep:Мало спал'},{'text':'Пропустить','callback_data':'morning:skip'}]])

def checkin_open(period):
    clock=now().strftime('%H:%M')
    return ('07:30'<=clock<'09:00') if period=='am' else ('18:00'<=clock<'20:00')

def reminder(period):
    table='morning_checkins' if period=='am' else 'evening_checkins'
    with conn() as c:users=c.execute('select u.id from users u left join '+table+" x on x.user_id=u.id and x.day=? where u.enabled=1 and (x.step is null or x.step not in ('done','closed'))",(today(),)).fetchall()
    for u in users:
        if period=='am':
            send(u['id'],'☀️ <b>08:30 / НАПОМИНАНИЕ</b>\nСобираю ваши ответы до 09:00. После 09:00 ответы не принимаю. Продолжи с прошлого сообщения или начни здесь.',[[{'text':'Ответить на утренние вопросы','callback_data':'morning:start'}]])
        else:
            send(u['id'],'🌙 <b>19:00 / НАПОМИНАНИЕ</b>\nСобираю вечерние ответы до 20:00. Продолжи с прошлого сообщения или начни здесь.',[[{'text':'Ответить на вечерние вопросы','callback_data':'evening:start'}]])

def close_checkin(period):
    table='morning_checkins' if period=='am' else 'evening_checkins'
    with conn() as c:
        c.execute("update "+table+" set step='closed',visible=0 where day=? and step not in ('done','closed')",(today(),))
        c.execute("update users set stage='' where stage like ?",(('morning:%' if period=='am' else 'evening:%'),))

def evening():
    with conn() as c: users=c.execute('select id from users where enabled=1').fetchall()
    for u in users:
        send(u['id'],'🌙 <b>18:00 / ВЕЧЕРНЯЯ ПЕРЕКЛИЧКА</b>\nКак прошёл день, какой момент запомнился и доволен ли ты? Ответы принимаю до 20:00.\n\n<b>1/3. Как прошёл день?</b>',[[{'text':'🙂 Хорошо','callback_data':'evening:day:Хороший'},{'text':'😐 Обычно','callback_data':'evening:day:Обычный'}],[{'text':'😮 Непросто','callback_data':'evening:day:Сложный'},{'text':'Пропустить','callback_data':'evening:skip'}]])

def scheduler():
    while True:
        try:
            t=now(); clock=t.strftime('%H:%M')
            if clock=='07:30':run_slot('morning',morning)
            if clock=='08:30':run_slot('morning-reminder',lambda:reminder('am'))
            if clock=='09:00':run_slot('morning-close',lambda:close_checkin('am'))
            if clock=='10:00':run_slot('digest-am',lambda:digest('am'))
            if clock=='15:00':run_slot('tip',tip)
            if clock=='16:00':quest_next_episodes()
            if clock=='18:00':run_slot('evening',evening)
            if clock=='19:00':run_slot('evening-reminder',lambda:reminder('pm'))
            if clock=='20:00':run_slot('evening-close',lambda:close_checkin('pm'))
            if clock=='20:30':run_slot('digest-pm',lambda:digest('pm'))
            if t.weekday() in (0,2) and clock=='16:00':run_slot('mission',mission)
            if t.weekday() in (1,4) and clock=='16:00':run_slot('instant-photo',instant_photo)
            if t.weekday() in (1,4) and clock=='20:30':run_slot('photos-digest',photos_digest)
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
        parts=text.split(maxsplit=1)
        target=parts[1].strip().lower() if len(parts)==2 else ''
        if target in ('kids','media'):
            with conn() as c:c.execute("insert into settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value",('quest_chat_'+target,str(chat['id'])))
            send(str(chat['id']),'🎬 <b>'+('Kids Lab' if target=='kids' else 'Media Lab')+'</b>: этот чат подключён для утверждённых квестов.')
            return
        GROUP=str(chat['id'])
        with conn() as c:c.execute("insert into settings(key,value) values('group_chat',?) on conflict(key) do update set value=excluded.value",(GROUP,))
        send(GROUP,'🎬 <b>TIMECODE подключён к этому чату.</b> Утренняя сводка выйдет после следующей переклички.')
        return
    if chat.get('type') in ('group','supergroup') and str(chat.get('id'))==GROUP and text.startswith('/ask') and allowed(uid):
        question=text.split(' ',1)[1].strip() if ' ' in text else ''
        if not question:send(GROUP,'Чтобы спросить, напиши /ask и свой вопрос.');return
        delivered=ask_admins(uid,question)
        if delivered:send(GROUP,'Вопрос передан преподавателю. Ответ придёт автору лично в бот.')
        return
    if chat.get('type')!='private' or not uid:return
    start=text.partition(' ')[2] if text.startswith('/start') else ''
    first_join=not allowed(uid)
    if first_join:
        roster(uid,' '.join(filter(None,[msg.get('from',{}).get('first_name',''),msg.get('from',{}).get('last_name','')])) or 'Участник')
    if text.startswith('/start'):
        if start=='instant':
            if now().weekday() not in (1,4) or now().strftime('%H:%M')<'16:00' or now().strftime('%H:%M')>='20:00':
                send(uid,'Мгновенный кадр принимаю по вторникам и пятницам с 16:00 до 20:00.');return
            with conn() as c:c.execute("update users set stage='instant' where id=?",(uid,))
            send(uid,'📸 Сфоткай то, что сейчас перед тобой, и отправь сюда одно фото до 20:00. В 20:30 покажу кадры в общем чате. Если не хочешь участвовать — просто не присылай.');return
        if start=='mission':
            with conn() as c:c.execute("update users set stage='mission' where id=?",(uid,))
            send(uid,'🎬 Пришли ответ на сегодняшнее задание: фото или одну короткую фразу.');return
        keys=[[{'text':'Открыть TIMECODE ↗','web_app':{'url':BASE}}]] if BASE else []
        if uid in ADMINS:keys += [[{'text':'📣 Написать всем','callback_data':'admin:publish'},{'text':'❓ Вопросы','callback_data':'admin:questions'}]]
        if first_join:
            keys += [[{'text':'Я в Kids Lab','callback_data':'onboard:lab:kids'},{'text':'Я в Media Lab','callback_data':'onboard:lab:media'}]]
            name=esc(msg.get('from',{}).get('first_name','').strip()[:40] or 'друг')
            send(uid,'🎬 <b>Привет, '+name+'! Я TIMECODE.</b>\nБот медиацентра «Марфино». Будем на связи каждый день: утром спрошу, как начался день, вечером — что запомнилось. Из ваших ответов соберу живую сводку группы. Не хочется отвечать — можно пропустить.\n\n⏱ В 15:00 принесу короткий лайфхак про кино и съёмку. Во вторник и пятницу предложу снять мгновенный кадр.\n\n📱 В приложении найдёшь <b>расписание, игры и уроки</b> — можно вернуться к тем, что уже проходили.\n\nЯ пока только учусь и буду расти вместе с вами. Выбери свою лабораторию ниже и заглядывай в приложение. Начнём?',keys)
        else:
            send(uid,'🎬 <b>TIMECODE на связи.</b> Расписание, игры и уроки — в приложении. Я здесь, если захочешь задать вопрос или присоединиться к сегодняшнему выпуску.',keys)
        return
    if uid in ADMINS and text in ('/publish','📣 Написать всем'):
        with conn() as c:c.execute("update users set stage='admin_publish' where id=?",(uid,))
        send(uid,'📣 Напиши сообщение или отправь фото, видео либо документ. Бот разошлёт его всем лично и продублирует во взрослый чат, если тот подключён. /stop — отмена.')
        return
    if uid in ADMINS and text.startswith('/quest '):
        send(uid,'Выпуск текстовых квестов остановлен. Готовим визуальную игру: сцены, действия, анимация и разветвления. Черновики не публикуются.')
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
    if uid in ADMINS and text.startswith('/ai'):
        option=text.partition(' ')[2].strip().lower()
        if option in ('on','off'):
            with conn() as c:
                c.execute("insert into settings(key,value) values('creative_ai',?) on conflict(key) do update set value=excluded.value",(option,))
                c.execute('delete from daily_content where day=? and kind in (?,?)',(today(),'tip','mission'))
            send(uid,'Самостоятельные лайфхаки и задания Kimi '+('включены.' if option=='on' else 'выключены. Будет выпускаться редакционный банк.'))
        else:send(uid,'Экспериментальные идеи Kimi: '+('включены' if creative_enabled() else 'выключены')+'. Управление: /ai on или /ai off.')
        return
    if text.startswith('/schedule') and uid in ADMINS:
        send(uid,'Добавить занятие: /lesson kids Пн 18:00 | Название | Кабинет\nОтмена или замена на дату: /change kids 2026-10-01 18:00 | Новая тема | Кабинет\nОтмена: /cancel kids 2026-10-01');return
    if uid in ADMINS and text.startswith('/help'):
        send(uid,'<b>РЕДАКЦИЯ TIMECODE</b>\n/send Текст — написать всем. Фото, видео или документ с подписью <code>/send Текст</code> — отправить файл всем.\n/reply № Текст — ответить ученику; можно ответить прямо на сообщение с вопросом, включая фото или файл.\n/ai off — отключить новые лайфхаки и задания Kimi; /ai on — вернуть.\n/invite — приглашение; /schedule — расписание; /quiet — личные переклички.');return
    if uid in ADMINS and text=='/stop':
        with conn() as c:c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'Действие отменено.');return
    if uid in ADMINS and text.startswith('/reply '):
        parts=text.split(' ',2)
        if len(parts)<3 or not parts[1].isdigit():send(uid,'Напиши: /reply 12 Текст ответа');return
        answer_question(uid,int(parts[1]),parts[2]);return
    if uid in ADMINS and msg.get('reply_to_message'):
        reply_id=msg['reply_to_message'].get('message_id')
        with conn() as c:receipt=c.execute('select question_id from question_receipts where admin_id=? and message_id=?',(uid,reply_id)).fetchone()
        if receipt:
            reply_text=(msg.get('caption') or text).strip()
            if not reply_text and not (msg.get('photo') or msg.get('document') or msg.get('video')):
                send(uid,'Пришли текст, фото, видео или документ в ответ на вопрос.');return
            answer_question(uid,receipt['question_id'],reply_text,msg if msg.get('photo') or msg.get('document') or msg.get('video') else None);return
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
    caption=(msg.get('caption') or '').strip()
    if uid in ADMINS and (text.startswith('/send ') or caption.startswith('/send')):
        body=(text if text.startswith('/send ') else caption)[5:].strip()
        if not body and not (msg.get('photo') or msg.get('document') or msg.get('video')):
            send(uid,'Добавь текст после /send или отправь файл с подписью /send Название.');return
        sent,failed=publish_to_all(msg,body)
        send(uid,'Отправлено: '+str(sent)+'. Не доставлено: '+str(failed)+'.');return
    if uid not in ADMINS and text.startswith('/ask '):
        question=text[5:].strip()
        if not question:send(uid,'Напиши вопрос после /ask.');return
        if ask_admins(uid,question):send(uid,'Вопрос ушёл преподавателю. Ответ придёт сюда.')
        else:send(uid,'Пока не получилось передать вопрос. Попробуй чуть позже.')
        return
    with conn() as c: u=c.execute('select stage from users where id=?',(uid,)).fetchone()
    stage=u['stage'] if u else ''
    if uid in ADMINS and stage=='admin_publish':
        body=(msg.get('caption') or text).strip()
        if not body and not (msg.get('photo') or msg.get('document') or msg.get('video')):send(uid,'Пришли текст, фото, видео или документ. /stop — отменить.');return
        sent,failed=publish_to_all(msg,body)
        if sent:
            with conn() as c:c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'Отправлено: '+str(sent)+'. Не доставлено: '+str(failed)+('.' if sent else ' Режим публикации сохранён.'));return
    if uid in ADMINS and stage.startswith('admin_question:'):
        question_id=int(stage.split(':')[1]);response_text=(msg.get('caption') or text).strip()
        if not response_text and not (msg.get('photo') or msg.get('document') or msg.get('video')):send(uid,'Пришли ответ текстом или файлом. /stop — отменить.');return
        answer_question(uid,question_id,response_text,msg if msg.get('photo') or msg.get('document') or msg.get('video') else None)
        with conn() as c:c.execute("update users set stage='' where id=?",(uid,))
        return
    photo=msg.get('photo',[])[-1]['file_id'] if msg.get('photo') else ''
    if stage=='instant':
        if now().weekday() not in (1,4) or not '16:00'<=now().strftime('%H:%M')<'20:00':
            with conn() as c:c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'Сбор мгновенных кадров уже закончился.');return
        if not photo:send(uid,'Отправь одно фото. Можно просто не участвовать.');return
        commentary=photo_comment(photo)
        with conn() as c:
            c.execute("insert into missions(user_id,day,kind,answer,photo,published,comment) values(?,?,'instant','',?,1,?) on conflict(user_id,day) do update set kind='instant',answer='',photo=excluded.photo,published=1,comment=excluded.comment",(uid,today(),photo,commentary))
            c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'📸 Кадр принят. Сегодня в 20:30 увидишь его в общей подборке.');return
    if stage=='morning:important':
        if not checkin_open('am'):
            with conn() as c:c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'Утренний сбор завершён в 09:00. Завтра снова увидимся!');return
        if not text or text.startswith('/'):
            send(uid,'Напиши одной фразой, что сегодня важного, или нажми «Пропустить».',[[{'text':'Пропустить','callback_data':'morning:important:skip'}]]);return
        with conn() as c:
            row=c.execute('select step from morning_checkins where user_id=? and day=?',(uid,today())).fetchone()
            if not row or row['step']!='important':return
            c.execute("update morning_checkins set important=?,step='done',visible=1 where user_id=? and day=?",(text[:160],uid,today()))
            c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'Спасибо! Утренняя сводка появится в 10:00.');return
    if stage=='mission':
        if not photo and not text:send(uid,'Пришли фото или короткую фразу.');return
        kind=daily_content('mission')['mode']
        if kind=='photo' and not photo:send(uid,'Сегодня фото задание. Отправь один кадр.');return
        with conn() as c:
            c.execute('insert into missions(user_id,day,kind,answer,photo,published) values(?,?,?,?,?,1) on conflict(user_id,day) do update set answer=excluded.answer,photo=excluded.photo,published=1',(uid,today(),kind,(msg.get('caption') or text)[:400],photo))
            c.execute("update users set stage='' where id=?",(uid,))
        send(uid,'Ответ на задание сохранён.')
        return
    if stage=='evening:highlight':
        if not checkin_open('pm'):
            with conn() as c:c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'Вечерний сбор завершён в 20:00. До завтра!');return
        line=text.strip()
        if not line or line.startswith('/'):
            send(uid,'Одной короткой фразой — что сегодня запомнилось? Или нажми «Пропустить».',[[{'text':'Пропустить','callback_data':'evening:highlight:skip'}]])
            return
        with conn() as c:
            row=c.execute('select step from evening_checkins where user_id=? and day=?',(uid,today())).fetchone()
            if row and row['step']=='highlight':
                c.execute('update evening_checkins set highlight=?,step=? where user_id=? and day=?',(line[:150],'satisfied',uid,today()))
            c.execute("update users set stage='' where id=?",(uid,))
        if not row or row['step']!='highlight':send(uid,'Вечерняя перекличка на сегодня уже закончилась.');return
        send(uid,'<b>3/3. Ты доволен сегодняшним днём?</b>',[[{'text':'Да 🙂','callback_data':'evening:satisfied:Да'},{'text':'Не очень 😐','callback_data':'evening:satisfied:Не очень'}],[{'text':'Нет 🙁','callback_data':'evening:satisfied:Нет'}]])
        return
    question=(msg.get('caption') or text).strip()
    if uid in ADMINS:
        send(uid,'Для всех подписчиков: /send Текст или фото с подписью /send Текст. Вопросы учеников придут сюда; отвечай ответом на сообщение. /help — все команды.');return
    if question.startswith('/ask '):question=question[5:].strip()
    if question and not question.startswith('/'):
        if ask_admins(uid,question):send(uid,'Вопрос ушёл преподавателю. Ответ придёт сюда.')
        else:send(uid,'Пока не получилось передать вопрос. Попробуй чуть позже.')
        return
    send(uid,'Хочешь спросить преподавателя? Просто напиши вопрос одним сообщением. Открыть игры и расписание можно через меню бота.')

def callback(q):
    uid=q.get('from',{}).get('id');data=q.get('data','');msg=q.get('message',{});cid=msg.get('chat',{}).get('id')
    if not uid or not allowed(uid):return
    api('answerCallbackQuery',{'callback_query_id':q['id']})
    if data in ('onboard:lab:kids','onboard:lab:media'):
        lab=data.rsplit(':',1)[1]
        with conn() as c:c.execute('update users set lab=? where id=?',(lab,uid))
        label='Kids Lab' if lab=='kids' else 'Media Lab'
        send(uid,'🎬 Ты в '+label+'. Теперь расписание и задания будут для твоей лаборатории.'+(' Открой приложение — там уже есть чем заняться.' if BASE else ''),[[{'text':'Открыть TIMECODE ↗','web_app':{'url':BASE}}]] if BASE else None)
        return
    if uid in ADMINS and data.startswith('quest:'):
        try:_,action,raw_id=data.split(':',2);qid=int(raw_id)
        except (ValueError,TypeError):return
        with conn() as c:result=quests.review(c,uid,qid,action,today(),send,BASE)
        send(uid,result)
        return
    if uid in ADMINS and data=='admin:publish':
        with conn() as c:c.execute("update users set stage='admin_publish' where id=?",(uid,))
        send(uid,'📣 Отправь сообщение, фото, видео или документ. Разошлю каждому в личный бот и продублирую в чат взрослых, если он подключён. /stop — отменить.')
        return
    if uid in ADMINS and data=='admin:questions':
        with conn() as c:rows=c.execute('select q.id,q.body,u.name from questions q join users u on q.user_id=u.id where q.answered=0 order by q.id desc limit 5').fetchall()
        if not rows:send(uid,'Неотвеченных вопросов пока нет.');return
        for row in rows:
            send(uid,'❓ <b>ВОПРОС #'+str(row['id'])+'</b> от '+esc(row['name'])+'\n'+esc(row['body'][:300]),[[{'text':'Ответить ↗','callback_data':'admin:question:'+str(row['id'])}]])
        return
    if uid in ADMINS and data.startswith('admin:question:'):
        number=data.split(':')[-1]
        if not number.isdigit():return
        with conn() as c:
            row=c.execute('select answered from questions where id=?',(int(number),)).fetchone()
            if row and not row['answered']:c.execute('update users set stage=? where id=?',('admin_question:'+number,uid))
        if not row or row['answered']:send(uid,'На этот вопрос уже ответили.');return
        send(uid,'Ответь на вопрос #'+number+' следующим сообщением: текст, фото, видео или документ. /stop — отменить.')
        return
    if data.startswith('morning:'):
        if not checkin_open('am'):
            send(uid,'Утренние ответы принимаю с 07:30 до 09:00.');return
        parts=data.split(':',2); action=parts[1] if len(parts)>1 else '';value=parts[2] if len(parts)>2 else ''
        if action=='start':
            send(uid,'Как спалось?',[[{'text':'😌 Выспался','callback_data':'morning:sleep:Выспался'},{'text':'😐 Так себе','callback_data':'morning:sleep:Так себе'}],[{'text':'🥱 Мало спал','callback_data':'morning:sleep:Мало спал'},{'text':'Пропустить','callback_data':'morning:skip'}]]);return
        if action=='skip':
            with conn() as c:
                c.execute("insert into morning_checkins(user_id,day,step) values(?,?,'done') on conflict(user_id,day) do update set step='done',visible=0",(uid,today()))
                c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'Хорошо, завтра увидимся!');return
        if action=='sleep' and value in ('Выспался','Так себе','Мало спал'):
            with conn() as c:
                c.execute("insert into morning_checkins(user_id,day,sleep,step) values(?,?,?,'mood') on conflict(user_id,day) do update set sleep=excluded.sleep,step='mood',mood='',important='',photo='',visible=0",(uid,today(),value))
                c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'<b>2/3. Как дела?</b>',[[{'text':'🙂 Отлично','callback_data':'morning:mood:Отлично'},{'text':'😐 Нормально','callback_data':'morning:mood:Нормально'}],[{'text':'🙃 Не очень','callback_data':'morning:mood:Не очень'}]]);return
        if action=='mood' and value in ('Отлично','Нормально','Не очень'):
            with conn() as c:
                row=c.execute('select step from morning_checkins where user_id=? and day=?',(uid,today())).fetchone()
                if not row or row['step']!='mood':return
                c.execute("update morning_checkins set mood=?,step='important' where user_id=? and day=?",(value,uid,today()))
                c.execute("update users set stage='morning:important' where id=?",(uid,))
            send(uid,'<b>3/3. Что сегодня важного?</b> Одной фразой, если хочешь.',[[{'text':'Пропустить','callback_data':'morning:important:skip'}]]);return
        if action=='important' and value=='skip':
            with conn() as c:
                row=c.execute('select step from morning_checkins where user_id=? and day=?',(uid,today())).fetchone()
                if not row or row['step']!='important':return
                c.execute("update morning_checkins set step='done',visible=1 where user_id=? and day=?",(uid,today()))
                c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'Спасибо! Утренняя сводка появится в 10:00.');return
        return
    if data.startswith('evening:'):
        if not checkin_open('pm'):
            send(uid,'Вечерние ответы принимаю с 18:00 до 20:00.');return
        parts=data.split(':',2)
        action=parts[1] if len(parts)>1 else ''
        value=parts[2] if len(parts)>2 else ''
        if action=='start':
            send(uid,'<b>1/3. Как прошёл день?</b>',[[{'text':'🙂 Хорошо','callback_data':'evening:day:Хороший'},{'text':'😐 Обычно','callback_data':'evening:day:Обычный'}],[{'text':'😮 Непросто','callback_data':'evening:day:Сложный'},{'text':'Пропустить','callback_data':'evening:skip'}]]);return
        if action=='skip':
            with conn() as c:
                c.execute("insert into evening_checkins(user_id,day,step) values(?,?,'done') on conflict(user_id,day) do update set step='done',visible=0",(uid,today()))
                c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'Без вопросов. Завтра снова спросим, как дела.');return
        if action=='day' and value in ('Хороший','Обычный','Сложный'):
            with conn() as c:
                c.execute("insert into evening_checkins(user_id,day,mood,step) values(?,?,?,'highlight_choice') on conflict(user_id,day) do update set mood=excluded.mood,step='highlight_choice',highlight='',satisfied='',photo='',visible=0",(uid,today(),value))
                c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'<b>2/3. Был сегодня яркий момент?</b> Можно рассказать одной фразой.',[[{'text':'✨ Да, расскажу','callback_data':'evening:highlight:yes'},{'text':'Не было','callback_data':'evening:highlight:no'}],[{'text':'Пропустить','callback_data':'evening:highlight:skip'}]])
            return
        if action=='highlight' and value in ('yes','no','skip'):
            with conn() as c:
                row=c.execute('select step from evening_checkins where user_id=? and day=?',(uid,today())).fetchone()
                if not row or row['step']!='highlight_choice':return
                if value=='yes':
                    c.execute("update evening_checkins set step='highlight' where user_id=? and day=?",(uid,today()))
                    c.execute("update users set stage='evening:highlight' where id=?",(uid,))
                else:
                    c.execute('update evening_checkins set highlight=?,step=? where user_id=? and day=?',('Не было' if value=='no' else '','satisfied',uid,today()))
            if value=='yes':send(uid,'Расскажи одним предложением: что запомнилось сегодня?',[[{'text':'Пропустить','callback_data':'evening:detail:skip'}]])
            else:send(uid,'<b>3/3. Ты доволен сегодняшним днём?</b>',[[{'text':'Да 🙂','callback_data':'evening:satisfied:Да'},{'text':'Не очень 😐','callback_data':'evening:satisfied:Не очень'}],[{'text':'Нет 🙁','callback_data':'evening:satisfied:Нет'}]])
            return
        if action=='detail' and value=='skip':
            with conn() as c:
                row=c.execute('select step from evening_checkins where user_id=? and day=?',(uid,today())).fetchone()
                if not row or row['step']!='highlight':return
                c.execute("update evening_checkins set highlight='',step='satisfied' where user_id=? and day=?",(uid,today()))
                c.execute("update users set stage='' where id=?",(uid,))
            send(uid,'<b>3/3. Ты доволен сегодняшним днём?</b>',[[{'text':'Да 🙂','callback_data':'evening:satisfied:Да'},{'text':'Не очень 😐','callback_data':'evening:satisfied:Не очень'}],[{'text':'Нет 🙁','callback_data':'evening:satisfied:Нет'}]])
            return
        if action=='satisfied' and value in ('Да','Не очень','Нет'):
            with conn() as c:
                row=c.execute('select step from evening_checkins where user_id=? and day=?',(uid,today())).fetchone()
                if not row or row['step']!='satisfied':return
                c.execute("update evening_checkins set satisfied=?,step='done',visible=1 where user_id=? and day=?",(value,uid,today()))
            send(uid,'Спасибо! Вечерняя сводка появится в 20:30.')
            return
        return

def photos_digest():
    with conn() as c:rows=c.execute("select m.user_id,m.photo,m.comment,u.name from missions m join users u on m.user_id=u.id where m.day=? and m.kind='instant' and m.published=1",(today(),)).fetchall()
    if not rows:return
    pictures=[]
    for item in rows:
        if not item['photo']:continue
        comment=item['comment'] or photo_comment(item['photo'])
        if comment and not item['comment']:
            with conn() as c:c.execute("update missions set comment=? where user_id=? and day=? and kind='instant'",(comment,item['user_id'],today()))
        pictures.append({'photo':item['photo'],'name':item['name'],'comment':comment})
    for start in range(0,len(pictures),10):
        batch=pictures[start:start+10]
        if len(batch)>=2:
            media=[{'type':'photo','media':r['photo'],'caption':('📸 '+r['name']+'\n'+r['comment'] if r['comment'] else '📸 '+r['name'])[:850]} for r in batch]
            api('sendMediaGroup',{'chat_id':GROUP,'media':media})
        else:
            r=batch[0];api('sendPhoto',{'chat_id':GROUP,'photo':r['photo'],'caption':'📸 '+r['name']+('\n'+r['comment'] if r['comment'] else '')})

def polling():
    global BOTNAME
    me=api('getMe'); BOTNAME=(me.get('result') or {}).get('username','')
    if BOTNAME and BASE:
        api('setChatMenuButton',{'menu_button':{'type':'web_app','text':'Открыть TIMECODE','web_app':{'url':BASE}}})
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
            current=now()
            tip_item=daily_content('tip') if current.strftime('%H:%M')>='15:00' else None
            mission_item=daily_content('mission') if current.weekday() in (0,2,4) and current.strftime('%H:%M')>='16:00' else None
            personal_mission=((mission_item['body_media'] if u['lab']=='media' else mission_item['body_kids']) or mission_item['body']) if mission_item else ''
            with conn() as c:campaigns=quests.state(c,u['id'],u['lab'],u['role']=='admin',today())
            return self.out({'quests':campaigns,'me':{'id':u['id'],'name':u['name'],'lab':u['lab'],'role':u['role'],'enabled':bool(u['enabled'])},'lessons':lessons,'changes':changes,'progress':progress,'latest':latest,'tip':[tip_item['title'],tip_item['body']] if tip_item else None,'mission':[mission_item['title'],personal_mission,mission_item['mode']] if mission_item else None,'date':today(),'bot':BOTNAME})
        if path not in ('/','/app.js','/style.css','/framequest.js','/framequest.css','/nightshift.js','/nightshift.css','/terms-memory.js','/terms-memory.css','/arcade.js','/arcade.css','/glossary.js','/glossary.css'):return self.out({'error':'Не найдено'},404)
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
        if path=='/api/quest/choose':
            try:
                qid=int(p['id']);choice=p['choice']
                with conn() as c:effect=quests.choose(c,qid,u['id'],u['lab'],choice,today())
                return self.out({'ok':True,'effect':effect})
            except (KeyError,ValueError,OverflowError) as error:return self.out({'error':str(error)},400)
        if path=='/api/game':
            if p.get('game') not in ('cinema','shot','interview','differences','framing','moon','words'):return self.out({'error':'Неизвестная игра'},400)
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

import notification_delivery
notification_delivery.install(globals())

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
