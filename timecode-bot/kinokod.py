"""TIMECODE KinoKod 20-23 October 2026; isolated campaign."""
import datetime as dt
import hashlib
import json
import time

CAMPAIGN = 'kinokod20261020'
TZ = dt.timezone(dt.timedelta(hours=3))
RELEASES = [
 ('2026-10-20T12:00:00+03:00', 'Дело открыто', '🎬 КИНОКОД. На съёмках исторического фильма в Сириусе исчезла старинная кинокамера. Внутри была плёнка с другой концовкой. Часы в реквизиторской остановились на 17:24. Что проверим первым?', ['Часы', 'Футляр камеры', 'Журнал реквизита']),
 ('2026-10-20T18:30:00+03:00', 'Следы времени', '🕰 Снимите или нарисуйте предмет со стрелками: часы, компас, циферблат. Отправьте фото ответом на это задание. Никаких чужих лиц и геометок. Кими изучит находки; лучшие станут частью пятничного репортажа.', None),
 ('2026-10-21T09:00:00+03:00', 'Три подозреваемых', '🕵 Оператор: «Я настраивал свет». Гримёрша: «Весь день клеила бороду царю». Реквизитор: «Я проверял шкаф до 17:24». Чьё алиби сначала проверить?', ['Оператор', 'Гримёрша', 'Реквизитор']),
 ('2026-10-21T18:30:00+03:00', 'Допрос', '🔎 Камера в последний раз попала в кадр возле открытого шкафа. Кому зададим решающий вопрос?', ['Оператору о записи', 'Гримёрше о плёнке', 'Реквизитору о шкафе']),
 ('2026-10-22T09:00:00+03:00', 'Кадр №24', '🎞 Монтажёр нашёл записку: «Правильный финал не тот, что в сценарии». На обороте: СВЕТ · ЛИЦО · ПРАВДА. Какая подсказка важнее?', ['Свет', 'Лицо', 'Правда']),
 ('2026-10-22T18:30:00+03:00', 'Твоя киноулика', '📸 Сними крупным планом обычный предмет так, чтобы он выглядел как улика. Отправь одно фото или рисунок и подпись из 3–8 слов. Не фотографируй посторонних без согласия.', None),
 ('2026-10-23T09:00:00+03:00', 'Последняя версия', '🎬 До премьеры несколько часов. Кто спрятал камеру? Проголосуй. Кими посчитает версии и выберет героя финального репортажа.', ['Оператор', 'Гримёрша', 'Реквизитор']),
]
ENDING = {
 0: 'Главный герой сегодняшнего репортажа — оператор. Оказалось, именно он заснял перенос старой камеры и сохранил улику, хотя сначала молчал.',
 1: 'Главная героиня репортажа — гримёрша. Она знала секрет альтернативной концовки и хотела сохранить плёнку, а не уничтожить её.',
 2: 'Главный герой репортажа — реквизитор. Именно он спрятал камеру по просьбе гримёрши, чтобы плёнку не перезаписали.'
}
TRUTH = 'Истина: реквизитор спрятал камеру по просьбе гримёрши, а оператор случайно снял перенос. Плёнку спасли, но скрытность едва не сорвала съёмку. Лучший финал — когда съёмочная группа знает правду.'
def tables(c):
    c.executescript("""create table if not exists kinokod_votes (user_id integer not null, slot integer not null, choice integer, photo text, caption text, updated integer not null, primary key(user_id,slot));
create table if not exists kinokod_posts (slot integer primary key, sent_at integer not null);""")

def install(s):
    old_message=s['bot_message']
    old_callback=s['callback']
    old_reminders=s['class_reminders']
    def eligible(uid):
        with s['conn']() as c:
            r=c.execute('select role, enabled from users where id=?',(uid,)).fetchone()
            if not r or not r['enabled'] or r['role']=='admin':return False
            if r['role']=='teacher':
                t=c.execute("select name from sqlite_master where type='table' and name='teacher_modes'").fetchone()
                if not t:return False
                t=c.execute('select daily_enabled from teacher_modes where user_id=?',(uid,)).fetchone()
                return bool(t and t['daily_enabled'])
            return True
    def now():return s['now']()
    def buttons(slot):
        opts=RELEASES[slot][3]
        if opts:
            return [[{'text':o,'callback_data':f'kc:{slot}:{i}'}] for i,o in enumerate(opts)]
        return [[{'text':'📷 Отправлю фото','callback_data':f'kc:{slot}:photo'}]]
    def record(uid,slot,choice=None,photo=None,caption=''):
        with s['conn']() as c:
            tables(c)
            c.execute('insert into kinokod_votes(user_id,slot,choice,photo,caption,updated) values(?,?,?,?,?,?) on conflict(user_id,slot) do update set choice=excluded.choice,photo=excluded.photo,caption=excluded.caption,updated=excluded.updated',(uid,slot,choice,photo,caption,int(time.time())))
    def callback(q):
        data=q.get('data','')
        if not data.startswith('kc:'):return old_callback(q)
        uid=(q.get('from') or {}).get('id')
        if q.get('id')!='max':s['api']('answerCallbackQuery',{'callback_query_id':q.get('id')})
        if not uid or not eligible(uid):return
        try:_,a,b=data.split(':');slot=int(a)
        except ValueError:return
        if not 0<=slot<len(RELEASES) or now()<dt.datetime.fromisoformat(RELEASES[slot][0]):return
        if b=='photo' and slot in (1,5):
            with s['conn']() as c:
                tables(c)
                c.execute('insert or ignore into kinokod_votes(user_id,slot,updated) values(?,?,?)',(uid,slot,int(time.time())))
            s['send'](uid,'Теперь отправь одно фото или рисунок ответом в этот чат. Кими сохранит улику для расследования.')
            return
        try:choice=int(b)
        except ValueError:return
        if RELEASES[slot][3] is None or not 0<=choice<3:return
        record(uid,slot,choice=choice)
        s['send'](uid,'🔍 Версия принята. Кими сохранил твой выбор. Следующая улика появится по расписанию.')
    def message(msg):
        uid=(msg.get('from') or {}).get('id')
        if not uid or (msg.get('chat') or {}).get('type')!='private' or not eligible(uid):return old_message(msg)
        text=(msg.get('text') or '').strip()
        if text in ('/kinokod','/кинокод','Кинокод'):
            for i,r in enumerate(RELEASES):
                if now()>=dt.datetime.fromisoformat(r[0]):
                    s['send'](uid,'🎬 '+r[1]+'\n\n'+r[2],buttons(i))
            return
        media=msg.get('photo')
        caption=(msg.get('caption') or '').strip()
        if media and dt.datetime.fromisoformat(RELEASES[1][0])<=now()<dt.datetime.fromisoformat('2026-10-23T18:30:00+03:00'):
            with s['conn']() as c:
                tables(c)
                active=[x['slot'] for x in c.execute('select slot from kinokod_votes where user_id=? and slot in (1,5) and photo is null order by slot desc',(uid,)).fetchall()]
            if active:
                slot=active[0]
                photo_id=media[-1].get('file_id') if isinstance(media,list) else ''
                if photo_id:
                    record(uid,slot,photo=photo_id,caption=caption[:250])
                    s['send'](uid,'📷 Улика сохранена. Кими добавит её к материалам расследования.')
                    return
        return old_message(msg)
    def post(slot):
        at,title,body,opts=RELEASES[slot]
        with s['conn']() as c:
            tables(c)
            inserted=c.execute('insert or ignore into kinokod_posts(slot,sent_at) values(?,?)',(slot,int(time.time()))).rowcount
            if not inserted:return
            users=[r['id'] for r in c.execute('select id from users where enabled=1').fetchall()]
            key='kc-'+CAMPAIGN+'-'+str(slot)
            for uid in users:
                if not eligible_for_conn(c,uid):continue
                c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(at[:10],key,json.dumps(uid),s['esc']('🎬 КИНОКОД · '+title+'\n\n'+body),json.dumps(buttons(slot),ensure_ascii=False)))
        s['retry_notifications'](key)
    def eligible_for_conn(c,uid):
        r=c.execute('select role from users where id=?',(uid,)).fetchone()
        if not r or r['role']=='admin':return False
        if r['role']=='teacher':
            t=c.execute("select name from sqlite_master where type='table' and name='teacher_modes'").fetchone()
            if not t:return False
            t=c.execute('select daily_enabled from teacher_modes where user_id=?',(uid,)).fetchone()
            return bool(t and t['daily_enabled'])
        return True
    def finale():
        with s['conn']() as c:
            tables(c)
            if c.execute('select slot from kinokod_posts where slot=7').fetchone():return
            rows=c.execute('select choice,count(*) as votes from kinokod_votes where slot=6 and choice is not null group by choice order by votes desc, choice asc').fetchall()
            winner=int(rows[0]['choice']) if rows else 2
            text='🎬 КИНОКОД · ФИНАЛ\n\n'+ENDING[winner]+'\n\n'+TRUTH+'\n\nКадр закрыт. А настоящие детективы знают: доказательства важнее догадок.'
            users=[r['id'] for r in c.execute('select id from users where enabled=1').fetchall()]
            c.execute('insert or ignore into kinokod_posts(slot,sent_at) values(7,?)',(int(time.time()),))
            key='kc-'+CAMPAIGN+'-final'
            for uid in users:
                if eligible_for_conn(c,uid):
                    c.execute('insert or ignore into notification_outbox(day,message_key,chat,body) values(?,?,?,?)',('2026-10-23',key,json.dumps(uid),s['esc'](text)))
        s['retry_notifications'](key)
    def tick():
        clock=now()
        for i,r in enumerate(RELEASES):
            if clock>=dt.datetime.fromisoformat(r[0]) and clock<dt.datetime.fromisoformat('2026-10-24T00:00:00+03:00'):post(i)
        if clock>=dt.datetime.fromisoformat('2026-10-23T19:00:00+03:00') and clock<dt.datetime.fromisoformat('2026-10-25T00:00:00+03:00'):finale()
    def reminders():
        tick()
        return old_reminders()
    s.update(bot_message=message,callback=callback,class_reminders=reminders,kinokod_tick=tick)
