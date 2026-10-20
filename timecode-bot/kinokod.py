"""TIMECODE KinoKod 20-23 October 2026; isolated campaign."""
import datetime as dt
import hashlib
import json
import time
import threading
from pathlib import Path

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

# This is the deterministic case file. Kimi may interpret, but never invent evidence.
CASE_RAILS = {
 0: {
  'reveal': [
   'За стеклом часов обнаружилась царапина: стрелки не сломались, кто-то снял крышку. Значит, 17:24 может быть подставной отметкой.',
   'На футляре серебристая пыль. Такой порошок есть на двери реквизиторского шкафа. Но это ещё не значит, что камеру переносил реквизитор.',
   'В журнале запись «камера на месте» исправлена поверх другого времени. На полях карандашом стоит «7Б». Кто-то переписывал хронологию.'
  ],
  'question': 'Кими: одна улика — ещё не приговор. Как проверим версию?',
  'moves': ['Сверить время хлопушки','Изучить маршрут','Открыть лист смены'],
  'outcomes': [
   'На хлопушке последнего дубля стоит 17:19. Часы остановились позже. Между этими минутами кто-то успел попасть за декорации.',
   'На плане площадки нашёлся короткий проход от исторической улицы к реквизиторскому шкафу. Именно там могли оставить тяжёлый футляр.',
   'В листе смены есть пометка «перенос футляра, 17:26», но не указано, кто его нёс. Почерк напоминает запись из журнала.'
  ],
  'end': '📁 ДЕЛО №1 НЕ ЗАКРЫТО. Теперь у нас есть маршрут и временной промежуток, а не просто подозрения. Сегодня в 18:30 мск проверим время на твоей собственной фотоулике.'
 },
 2: {
  'reveal': [
   'Оператор не соврал про свет, но в списке дублей после 17:20 нет ни одного его крупного плана. Возможно, он наблюдал за проходом.',
   'Гримёрша действительно работала с актёрами, но за час до пропажи попросила оставить старую плёнку отдельно от новой.',
   'Реквизитор отмечал предметы, но ключ от шкафа не записал ни на кого. На схеме площадки этот шкаф стоит рядом с тайным проходом.'
  ],
  'question': 'Кими: у каждого есть алиби, но у каждого есть пробел. Какой документ запросим?',
  'moves': ['Съёмочное расписание','Общий план площадки','Книгу выдачи ключей'],
  'outcomes': [
   'В расписании перерыв длился всего семь минут. Времени на дальний вынос камеры не было, зато до шкафа рукой подать.',
   'На общем плане не видно лица человека с футляром, зато видна дверь шкафа и тень от декорации.',
   'Ключ от шкафа остался на крючке после 17:00. Значит, доступ имел не только реквизитор.'
  ],
  'end': '🗃️ ПРОТОКОЛ ДОПОЛНЕН. Теперь подозреваем не профессию, а поступок. Сегодня в 18:30 мск устроим допрос по конкретной детали.'
 },
 3: {
  'reveal': [
   'Оператор подтверждает: в архивной записи есть движение возле шкафа, но лицо закрывает декорация. Он готов показать кадр.',
   'Гримёрша говорит: альтернативная концовка была снята на старую плёнку. Она боялась, что её сотрут при монтаже.',
   'Реквизитор признаёт: шкаф открывали после репетиции. Но утверждает, что делал это не один.'
  ],
  'question': 'Кими: показания записаны. Как не испортить расследование поспешным выводом?',
  'moves': ['Сохранить протокол','Запросить исходный кадр','Сопоставить времена'],
  'outcomes': [
   'Записали показания дословно. Две версии сходятся в одном: кто-то опасался за судьбу плёнки.',
   'Исходный кадр показывает только силуэт с большим предметом. Лицо не видно, зато направление движения совпадает с планом.',
   'Отметки 17:19, 17:24 и 17:26 образовали цепочку. Между съёмкой и записью в журнале была короткая пауза.'
  ],
  'end': '🎞️ ДОПРОС ОКОНЧЕН. У нас есть причина искать именно плёнку, а не дорогую камеру. Завтра в 09:00 мск заглянем в монтажную.'
 },
 4: {
  'reveal': [
   'Слово «СВЕТ» встречается в пометке оператора к последнему дублю. Возможно, надо искать исходную съёмку.',
   'Слово «ЛИЦО» помечено на гримёрном листе: в альтернативном финале герой выглядит иначе, чем в сценарии.',
   'Слово «ПРАВДА» подчёркнуто в заметке режиссёра. Похоже, спор был не о технике, а о том, какую концовку показать зрителям.'
  ],
  'question': 'Кими: одно слово тянет за собой целую сцену. Что исследуем дальше?',
  'moves': ['Монтажный лист','Дело с запиской','Второй вариант финала'],
  'outcomes': [
   'В монтажном листе обнаружили пустое место для ещё одной катушки. Она должна была лежать рядом с камерой.',
   'На обороте записки виден след от скрепки. Значит, записка раньше была прикреплена к настоящему документу.',
   'В списке дублей второй финал не помечен как брак. Плёнку могли убрать, чтобы её не перезаписали.'
  ],
  'end': '🧩 КАРТИНА СКЛАДЫВАЕТСЯ. Пока неизвестно, кто спрятал камеру, но мотив становится понятнее. Сегодня в 18:30 мск создадим фотоулику, а завтра назовём подозреваемого.'
 },
 6: {
  'reveal': [
   'Ты подозреваешь оператора. Его съёмка может быть и доказательством, и попыткой скрыть собственный след.',
   'Ты подозреваешь гримёршу. Она действительно защищала плёнку, но это ещё не ответ на вопрос, кто перенёс камеру.',
   'Ты подозреваешь реквизитора. У него были доступ к шкафу и знания о маршруте. Но нужна причина, а не только возможность.'
  ],
  'question': 'Кими: кого обвиняем, я записал. А какой мотив проверим перед финалом?',
  'moves': ['Спасти старую плёнку','Скрыть ошибку группы','Разыграть режиссёра'],
  'outcomes': [
   'Версия о спасении плёнки объясняет, почему камера исчезла вместе с катушкой. Но действовать тайно было опасно для съёмок.',
   'Версия об ошибке объясняет молчание, но не объясняет записку про «правильный финал». Придётся искать ещё одно подтверждение.',
   'Версия о розыгрыше звучит эффектно для кино, но улики слишком серьёзные. Шутка без согласия команды могла сорвать премьеру.'
  ],
  'end': '🏁 ПОСЛЕДНЯЯ ВЕРСИЯ В ПРОТОКОЛЕ. Голоса сохранены. Сегодня в 19:00 мск Кими раскроет события и покажет, где мы ошибались.'
 }
}
PHOTO_CLOSURES = {
 1: '🕰 Кими открыл старый план: часы можно остановить рукой, но время на хлопушке не подделаешь так просто. В деле две отметки — 17:24 и 17:26. Кто объяснит разницу? Завтра в 09:00 мск опросим троих подозреваемых.',
 5: '🎞 В монтажной обнаружили свободную коробку под плёнку. Теперь ясно: исчезла не только камера, но и возможный другой финал картины. Завтра в 09:00 мск выбираем главную версию, в 19:00 узнаем правду.'
}

TRUTH = 'Истина: реквизитор спрятал камеру по просьбе гримёрши, а оператор случайно снял перенос. Плёнку спасли, но скрытность едва не сорвала съёмку. Лучший финал — когда съёмочная группа знает правду.'
def tables(c):
    c.executescript("""create table if not exists kinokod_votes (user_id integer not null, slot integer not null, choice integer, photo text, caption text, updated integer not null, primary key(user_id,slot));
create table if not exists kinokod_posts (slot integer primary key, sent_at integer not null);
create table if not exists kinokod_players (user_id integer primary key, joined_at integer not null);
create table if not exists kinokod_steps (user_id integer not null, slot integer not null, action integer not null, updated integer not null, primary key(user_id,slot));
create table if not exists kinokod_visuals (user_id integer not null, slot integer not null, delivered integer not null default 0, attempts integer not null default 0, next_at integer not null default 0, primary key(user_id,slot));""")

def install(s):
    old_message=s['bot_message']
    old_callback=s['callback']
    old_reminders=s['class_reminders']
    def eligible(uid):
        with s['conn']() as c:
            r=c.execute('select role, enabled from users where id=?',(uid,)).fetchone()
            if not r or not r['enabled']:return False
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
        return [[{'text':'📷 Отправлю фото','callback_data':f'kc:{slot}:photo'}], [{'text':'📄 Продолжить без фотографии','callback_data':f'kc:{slot}:skip'}]]
    def record(uid,slot,choice=None,photo=None,caption=''):
        with s['conn']() as c:
            tables(c)
            c.execute('insert into kinokod_votes(user_id,slot,choice,photo,caption,updated) values(?,?,?,?,?,?) on conflict(user_id,slot) do update set choice=excluded.choice,photo=excluded.photo,caption=excluded.caption,updated=excluded.updated',(uid,slot,choice,photo,caption,int(time.time())))
    def send_visual(uid,slot):
        """Send an original illustrated scene as an actual image on each platform."""
        image=(Path(__file__).parent/'static'/('kinokod-'+str(slot)+'.png'))
        if not image.is_file():return False
        data=image.read_bytes()
        if len(data)>4_000_000:return False
        import shared_media
        with s['conn']() as db:
            is_max=(uid<0 and s['max_transport'].internal_id(db,'max',-uid) is not None)
        caption=('🎬 КИНОКОД · '+('Начинаем расследование' if slot==-1 else RELEASES[slot][1]))[:250]
        if is_max:
            upload=s['max_transport'].api('POST','/uploads?type=image',s['MAX_TOKEN'])
            body,headers=shared_media.multipart({},'data',data)
            headers['Authorization']=s['MAX_TOKEN']
            result=json.loads(shared_media.request(upload['url'],body,headers))
            token=str(result.get('token') or next((v.get('token') for v in (result.get('photos') or {}).values() if isinstance(v,dict) and v.get('token')),''))
            if not token:return False
            response=s['max_transport'].send_image(-uid,token,s['esc'](caption),s['MAX_TOKEN'])
            return bool(response and response.get('ok'))
        body,headers=shared_media.multipart({'chat_id':str(uid),'caption':caption},'photo',data)
        result=json.loads(shared_media.request('https://api.telegram.org/bot'+s['TOKEN']+'/sendPhoto',body,headers,telegram=True))
        return bool(result.get('ok'))
    def retry_visuals():
        with s['conn']() as db:
            tables(db)
            rows=db.execute('select user_id,slot,attempts from kinokod_visuals where delivered=0 and next_at<=? order by slot,user_id limit 3',(int(time.time()),)).fetchall()
        for row in rows:
            uid,slot=row['user_id'],row['slot']
            if not eligible(uid):continue
            with s['conn']() as db:
                unreachable=db.execute("select 1 from notification_unreachable where chat=?",(json.dumps(uid),)).fetchone()
                if unreachable:
                    db.execute('update kinokod_visuals set delivered=-1 where user_id=? and slot=? and delivered=0',(uid,slot))
                    continue
            ok=False
            terminal=False
            try:ok=send_visual(uid,slot)
            except Exception as exc:
                code=getattr(exc,'code',None)
                terminal=(code in (400,403))
                print('KinoKod visual error:',type(exc).__name__,str(code) if code is not None else '',flush=True)
            with s['conn']() as db:
                db.execute('update kinokod_visuals set delivered=?,attempts=attempts+1,next_at=? where user_id=? and slot=? and delivered=0',(-1 if terminal else 1 if ok else 0,int(time.time())+(300 if not ok else 0),uid,slot))
    def kimi_answer(uid,slot,choice):
        selected=RELEASES[slot][3][choice]
        try:
            with s['conn']() as db:
                history=[{'episode':r['slot'],'answer':RELEASES[r['slot']][3][r['choice']]} for r in db.execute('select slot,choice from kinokod_votes where user_id=? and choice is not null order by slot',(uid,)) if r['slot']<len(RELEASES) and RELEASES[r['slot']][3] and r['choice'] is not None]
            obj=s['ai_json'](
                'Ты Кими, детектив TIMECODE, общаешься лично с подростком 12+. Ты режиссёр-иронист, не робот-тестировщик. На исторической площадке в Сириусе пропала камера с альтернативным финалом. Реальная разгадка скрыта до 23 октября: реквизитор спрятал камеру по просьбе гримёрши, оператор видел перенос. Не раскрывай этот факт сейчас. Предложи живую сюжетную реакцию с одной неожиданной деталью или уточняющим вопросом. Не выдумывай поступки ребёнка. Верни JSON {"reply":"..."}, от 70 до 320 символов.',
                json.dumps({'episode':slot,'choice':selected,'previous':history},ensure_ascii=False),200) if s.get('AI_KEY') else None
            reply=str((obj or {}).get('reply','')).strip()
            if 60<=len(reply)<=390:
                s['send'](uid,'🕵️ <b>Кими:</b> '+s['esc'](reply))
                return
        except Exception as error:
            print('KinoKod Kimi text:',type(error).__name__,flush=True)
        s['send'](uid,'🕵️ <b>Кими:</b> Версию '+s['esc'](selected)+' записал. Интересно, а кто и зачем остановил часы именно в 17:24? Не спеши с обвинениями: завтра проверим алиби.')
    def kimi_chat(uid,question):
        try:
            with s['conn']() as db:
                answers=[{'scene':r['slot'],'choice':RELEASES[r['slot']][3][r['choice']]} for r in db.execute('select slot,choice from kinokod_votes where user_id=? and choice is not null order by slot',(uid,)) if 0<=r['slot']<len(RELEASES) and RELEASES[r['slot']][3] and r['choice'] is not None]
            obj=s['ai_json'](
                'Ты Кими, живой детектив и режиссёр квеста TIMECODE «Кинокод» для детей 12+. Действие: историческая съёмочная площадка в Сириусе, пропала старая камера с альтернативным финалом. Отвечай на один вопрос участника конкретно и остроумно, как персонаж истории, до 350 знаков. НЕ ИЗОБРЕТАЙ новые улики, показания, имена, цифры, записки или события. Известные факты только: часы 17:24, футляр со следами серебристой пыли, запись о переносе 17:26, реквизиторский шкаф и записка о правильном финале. Варианты событий и новые открытия только из сценария. Если факта нет, скажи, что пока неизвестно, и пригласи проверить следующую улику. Не разглашай разгадку до вечера пятницы. Не собирай личные данные, не давай опасных советов. Ответ JSON {"reply":"..."}.',
                json.dumps({'question':question,'player_choices':answers,'date':s['today']()},ensure_ascii=False),230)
            reply=str((obj or {}).get('reply','')).strip()
            if 30<=len(reply)<=520:
                s['send'](uid,'🕵️ <b>Кими:</b> '+s['esc'](reply))
                return
        except Exception as error:
            print('KinoKod chat:',type(error).__name__,flush=True)
        s['send'](uid,'Кими сейчас не смог подготовить ответ. Твой вопрос получен; попробуй спросить ещё раз немного позже.')
    def kimi_photo(uid,photo,url,slot):
        try:
            import creative_digest
            observed=creative_digest.inspect_photo(s,photo,url)
            comment=observed[:550]
            with s['conn']() as db:
                db.execute('create table if not exists kinokod_visions(user_id integer not null,slot integer not null,comment text not null,updated integer not null,primary key(user_id,slot))')
                db.execute('insert into kinokod_visions(user_id,slot,comment,updated) values(?,?,?,?) on conflict(user_id,slot) do update set comment=excluded.comment,updated=excluded.updated',(uid,slot,comment,int(time.time())))
            s['send'](uid,'🎞 <b>Кими рассматривает твою улику:</b> '+s['esc'](comment))
        except Exception as error:
            print('KinoKod photo review:',type(error).__name__,flush=True)
            s['send'](uid,'📷 Улику сохранил. Рассмотреть детали кадра пока не получилось, но фотография останется в деле.')

    def continuation_buttons(slot):
        return [[{'text':label,'callback_data':f'kc:{slot}:next:{i}'}] for i,label in enumerate(CASE_RAILS[slot]['moves'])]
    def reveal_choice(uid,slot,choice):
        case=CASE_RAILS[slot]
        body='🕵️ <b>Кими открывает следующую улику:</b> '+s['esc'](case['reveal'][choice])+'\n\n'+s['esc'](case['question'])
        s['send'](uid,body,continuation_buttons(slot))
    def resolve_step(uid,slot,action):
        case=CASE_RAILS[slot]
        # A verified narrative result, not a free-form AI invention.
        text='🔎 <b>Проверка завершена:</b> '+s['esc'](case['outcomes'][action])+'\n\n'+s['esc'](case['end'])
        s['send'](uid,text)
    def existing_continuations():
        # Older players answered while the game only had one-question episodes.
        with s['conn']() as db:
            tables(db)
            rows=db.execute('select v.user_id,v.slot,v.choice from kinokod_votes v join kinokod_players p on p.user_id=v.user_id left join kinokod_steps k on k.user_id=v.user_id and k.slot=v.slot where k.user_id is null and v.choice is not null and v.slot in (0,2,3,4,6)').fetchall()
            pending=[]
            for row in rows:
                uid,slot,choice=row['user_id'],row['slot'],row['choice']
                if not 0<=choice<3 or not eligible_for_conn(db,uid):continue
                if now()<dt.datetime.fromisoformat(RELEASES[slot][0]):continue
                key=f'kc-bridge-{CAMPAIGN}-{slot}'
                body='🔎 <b>Кими вернулся с новой уликой!</b>\n\n'+s['esc'](CASE_RAILS[slot]['reveal'][choice])+'\n\n'+s['esc'](CASE_RAILS[slot]['question'])
                keyboard=json.dumps(continuation_buttons(slot),ensure_ascii=False)
                done=db.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(s['today'](),key,json.dumps(uid),body,keyboard)).rowcount
                if done:pending.append(key)
        for key in set(pending):s['retry_notifications'](key)
    def callback(q):
        data=q.get('data','')
        if not data.startswith('kc:'):return old_callback(q)
        uid=(q.get('from') or {}).get('id')
        if q.get('id')!='max':s['api']('answerCallbackQuery',{'callback_query_id':q.get('id')})
        if not uid or not eligible(uid):return
        bits=data.split(':')
        if len(bits) not in (3,4):return
        try:slot=int(bits[1])
        except ValueError:return
        if not 0<=slot<len(RELEASES) or now()<dt.datetime.fromisoformat(RELEASES[slot][0]):return
        b=bits[2]
        if len(bits)==4:
            if b!='next' or slot not in CASE_RAILS:return
            try: action=int(bits[3])
            except ValueError:return
            if action not in (0,1,2):return
            with s['conn']() as db:
                tables(db)
                chosen=db.execute('select choice from kinokod_votes where user_id=? and slot=?',(uid,slot)).fetchone()
                if chosen is None or chosen['choice'] is None:return
                inserted=db.execute('insert or ignore into kinokod_steps(user_id,slot,action,updated) values(?,?,?,?)',(uid,slot,action,int(time.time()))).rowcount
                db.execute('update notification_outbox set delivered=-2 where chat=? and message_key=? and delivered=0',(json.dumps(uid),f'kc-bridge-{CAMPAIGN}-{slot}'))
            if inserted:resolve_step(uid,slot,action)
            else:s['send'](uid,'✅ Этот шаг уже пройден. Улика сохранена, следующий выпуск придёт по расписанию.')
            return
        if b=='open' and slot==0:
            with s['conn']() as c:
                tables(c)
                c.execute('insert or ignore into kinokod_players(user_id,joined_at) values(?,?)',(uid,int(time.time())))
            s['send'](uid,'🎬 '+RELEASES[0][1]+'\n\n'+RELEASES[0][2],buttons(0))
            s['send'](uid,'🕵️ Я Кими, твой напарник по расследованию. Можешь спросить меня прямо здесь: «Кими, почему часы остановились на 17:24?»')
            return
        if b=='skip' and slot in (1,5):
            with s['conn']() as db:
                tables(db)
                prior=db.execute('select photo,caption from kinokod_votes where user_id=? and slot=?',(uid,slot)).fetchone()
                first=prior is None or (not prior['photo'] and not prior['caption'])
                if first:
                    db.execute('insert into kinokod_votes(user_id,slot,caption,updated) values(?,?,?,?) on conflict(user_id,slot) do update set caption=excluded.caption,updated=excluded.updated',(uid,slot,'SKIPPED',int(time.time())))
            s['send'](uid,s['esc'](PHOTO_CLOSURES[slot]) if first else '✅ Этот эпизод уже сохранён.')
            return
        if b=='photo' and slot in (1,5):
            with s['conn']() as c:
                tables(c)
                c.execute('insert or ignore into kinokod_votes(user_id,slot,updated) values(?,?,?)',(uid,slot,int(time.time())))
            s['send'](uid,'Теперь отправь одно фото или рисунок ответом в этот чат. Кими сохранит улику для расследования.')
            return
        try:choice=int(b)
        except ValueError:return
        if RELEASES[slot][3] is None or not 0<=choice<3:return
        with s['conn']() as db:
            tables(db)
            db.execute('insert or ignore into kinokod_players(user_id,joined_at) values(?,?)',(uid,int(time.time())))
            before=db.execute('select choice from kinokod_votes where user_id=? and slot=?',(uid,slot)).fetchone()
            first=before is None or before['choice'] is None
            if first:
                db.execute('insert into kinokod_votes(user_id,slot,choice,updated) values(?,?,?,?) on conflict(user_id,slot) do update set choice=excluded.choice,updated=excluded.updated',(uid,slot,choice,int(time.time())))
            else:choice=before['choice']
            completed=db.execute('select 1 from kinokod_steps where user_id=? and slot=?',(uid,slot)).fetchone()
        if completed:
            s['send'](uid,'✅ Улика и твой следующий ход уже сохранены. Не теряй нить: новый выпуск придёт по расписанию.')
            return
        reveal_choice(uid,slot,choice)
    def message(msg):
        uid=(msg.get('from') or {}).get('id')
        if not uid or (msg.get('chat') or {}).get('type')!='private' or not eligible(uid):return old_message(msg)
        text=(msg.get('text') or '').strip()
        if text in ('/kinokod','/кинокод','Кинокод'):
            for i,r in enumerate(RELEASES):
                if now()>=dt.datetime.fromisoformat(r[0]):
                    s['send'](uid,'🎬 '+r[1]+'\n\n'+r[2],buttons(i))
            return
        if text.lower() in ('продолжить расследование','следующая улика','что дальше?'):
            with s['conn']() as db:
                tables(db)
                row=db.execute('select v.slot,v.choice from kinokod_votes v join kinokod_players p on p.user_id=v.user_id left join kinokod_steps k on k.user_id=v.user_id and k.slot=v.slot where v.user_id=? and v.choice is not null and k.user_id is null and v.slot in (0,2,3,4,6) order by v.slot desc limit 1',(uid,)).fetchone()
            if row:
                reveal_choice(uid,row['slot'],row['choice'])
            else:
                s['send'](uid,'🎬 Последняя улика уже в деле. Новый эпизод появится по расписанию. Можешь спросить меня: «Кими, что известно о часах?»')
            return
        if text.lower().startswith(('кими,','кими:')):
            with s['conn']() as db:
                tables(db)
                joined=db.execute('select 1 from kinokod_players where user_id=?',(uid,)).fetchone()
            if joined:
                question=text[5:].strip()[:400]
                if len(question)<3:
                    s['send'](uid,'Спроси меня о какой-нибудь улике. Например: «Кими, почему часы остановились на 17:24?»')
                else:
                    s['send'](uid,'🔎 Кими изучает вопрос...')
                    threading.Thread(target=kimi_chat,args=(uid,question),daemon=True).start()
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
                    s['send'](uid,'📷 Улика получена. Изучаю, что действительно видно в кадре.')
                    s['send'](uid,s['esc'](PHOTO_CLOSURES[slot]))
                    threading.Thread(target=kimi_photo,args=(uid,photo_id,str((msg.get('max_photo') or {}).get('url') or ''),slot),daemon=True).start()
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
                if not eligible_for_conn(c,uid) or not c.execute('select 1 from kinokod_players where user_id=?',(uid,)).fetchone():continue
                c.execute('insert or ignore into kinokod_visuals(user_id,slot) values(?,?)',(uid,slot))
                c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(at[:10],key,json.dumps(uid),s['esc']('🎬 КИНОКОД · '+title+'\n\n'+body),json.dumps(buttons(slot),ensure_ascii=False)))
        s['retry_notifications'](key)
    def eligible_for_conn(c,uid):
        r=c.execute('select role from users where id=?',(uid,)).fetchone()
        if not r:return False
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
            rows=c.execute("select v.choice,count(*) as votes from kinokod_votes v join users u on u.id=v.user_id where v.slot=6 and v.choice is not null and u.role!='admin' group by v.choice order by votes desc, v.choice asc").fetchall()
            winner=int(rows[0]['choice']) if rows else 2
            text='🎬 КИНОКОД · ФИНАЛ\n\n'+ENDING[winner]+'\n\n'+TRUTH+'\n\nКадр закрыт. А настоящие детективы знают: доказательства важнее догадок.'
            users=[r['id'] for r in c.execute('select id from users where enabled=1').fetchall()]
            c.execute('insert or ignore into kinokod_posts(slot,sent_at) values(7,?)',(int(time.time()),))
            key='kc-'+CAMPAIGN+'-final'
            for uid in users:
                if eligible_for_conn(c,uid):
                    c.execute('insert or ignore into notification_outbox(day,message_key,chat,body) values(?,?,?,?)',('2026-10-23',key,json.dumps(uid),s['esc'](text)))
        s['retry_notifications'](key)
    def invitation():
        clock=now()
        day=clock.date().isoformat()
        if day not in ('2026-10-20','2026-10-21','2026-10-22','2026-10-23'):return
        # One invitation per person per day; no repeats for those who joined.
        key='kc-'+CAMPAIGN+'-invite-'+day
        with s['conn']() as c:
            tables(c)
            people=[r['id'] for r in c.execute('select id from users where enabled=1').fetchall()]
            intro=('Привет, следователи! 🎬 На связи Кими, ваш временно назначенный детектив! Сегодня у нас детектив! На съёмочной площадке '
                   'исторического фильма в Сириусе пропала старинная кинокамера. '
                   'Вступай в «Кинокод»: найдём улики, допросим подозреваемых и раскроем '
                   'тайну в пятницу. Нажми кнопку и начни расследование.')
            if day!='2026-10-20':
                intro='🔍 Это снова Кими. Я всё ещё ищу напарников: камера исчезла, а улик только больше. Вступай в «Кинокод» до пятничной развязки. Я расскажу, что мы уже узнали.'
            keyboard=[[{'text':'🔎 Начать расследование','callback_data':'kc:0:open'}]]
            for uid in people:
                if eligible_for_conn(c,uid) and not c.execute('select 1 from kinokod_players where user_id=?',(uid,)).fetchone():
                    c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(day,key,json.dumps(uid),s['esc'](intro),json.dumps(keyboard,ensure_ascii=False)))
                    c.execute('insert or ignore into kinokod_visuals(user_id,slot) values(?,-1)',(uid,))
        s['retry_notifications'](key)
    def tick():
        clock=now()
        if dt.datetime.fromisoformat('2026-10-20T12:00:00+03:00')<=clock<dt.datetime.fromisoformat('2026-10-24T00:00:00+03:00'):invitation()
        for i,r in enumerate(RELEASES):
            if clock>=dt.datetime.fromisoformat(r[0]) and clock<dt.datetime.fromisoformat('2026-10-24T00:00:00+03:00'):post(i)
        if clock>=dt.datetime.fromisoformat('2026-10-23T19:00:00+03:00') and clock<dt.datetime.fromisoformat('2026-10-25T00:00:00+03:00'):finale()
        retry_visuals()
        existing_continuations()
    def reminders():
        tick()
        return old_reminders()
    s.update(bot_message=message,callback=callback,class_reminders=reminders,kinokod_tick=tick)
