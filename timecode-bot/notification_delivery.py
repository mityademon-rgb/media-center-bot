"""The same daily broadcasts go to every subscriber and the connected adult chat."""
import datetime as dt
import hashlib
import html
import json
import re
import editorial_voice


def install(s):
    original_evening=s['evening']
    original_instant_photo=s['instant_photo']
    def audience():
        with s['conn']() as c:
            return [r['id'] for r in c.execute('select id from users where enabled=1')]

    def destinations():
        return list(dict.fromkeys(audience() + ([s['GROUP']] if s['GROUP'] else [])))

    def broadcast(message, keyboard=None, chats=None):
        key=hashlib.sha256(message.encode()).hexdigest()[:24]
        with s['conn']() as c:
            for chat in (destinations() if chats is None else chats):
                c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',
                          (s['today'](),key,json.dumps(chat),message,json.dumps(keyboard,ensure_ascii=False)))
        retry_notifications(key)

    def retry_notifications(key=None):
        with s['conn']() as c:
            rows=c.execute('select day,message_key,chat,body,keyboard from notification_outbox where day>=? and delivered=0 '+
                           ('and message_key=? ' if key else '')+'order by day,message_key,chat limit 40',
                           ((s['now']().date()-dt.timedelta(days=1)).isoformat(),key) if key else
                           ((s['now']().date()-dt.timedelta(days=1)).isoformat(),)).fetchall()
        for row in rows:
            try:
                result=s['send'](json.loads(row['chat']),row['body'],json.loads(row['keyboard']))
                if result and result.get('ok'):
                    with s['conn']() as c:
                        c.execute('update notification_outbox set delivered=1 where day=? and message_key=? and chat=?',
                                  (row['day'],row['message_key'],row['chat']))
            except Exception as error:
                print('Notification retry:',type(error).__name__,flush=True)
        retry_photos()

    def retry_photos():
        with s['conn']() as c:
            rows=c.execute('select day,period,chat,user_id,photo,caption from notification_photo_outbox where day>=? and delivered=0 order by day,period,chat limit 40',
                           ((s['now']().date()-dt.timedelta(days=1)).isoformat(),)).fetchall()
        for row in rows:
            try:
                chat=json.loads(row['chat'])
                if isinstance(chat,int) and chat<0:
                    token=row['photo'][len('max:image:'):]
                    result=s['max_transport'].send_image(-chat,token,s['esc'](row['caption']),s['MAX_TOKEN'])
                else:
                    result=s['send_attachment'](chat,{'photo':[{'file_id':row['photo']}]},row['caption'])
                if result and result.get('ok'):
                    with s['conn']() as c:
                        c.execute('update notification_photo_outbox set delivered=1 where day=? and period=? and chat=? and user_id=?',
                                  (row['day'],row['period'],row['chat'],row['user_id']))
            except Exception as error:
                print('Photo retry:',type(error).__name__,flush=True)
        with s['conn']() as c:
            c.execute("update daily_photos set status='done' where status='queued' and not exists (select 1 from notification_photo_outbox p where p.day=daily_photos.day and p.period='daily' and p.user_id=daily_photos.user_id and p.delivered=0)")

    def broadcast_checkin_photos(rows,period,story=None):
        label='📸 КАДР УТРА · ' if period=='am' else '📸 КАДР ВЕЧЕРА · '
        text_only=[]
        with s['conn']() as c:
            for chat in destinations():
                attached=False
                for row in rows:
                    photo=row['photo']
                    if not photo:continue
                    from_max=photo.startswith('max:image:')
                    to_max=isinstance(chat,int) and chat<0
                    if from_max!=to_max or photo=='max:image:received':continue
                    caption=(html.unescape(re.sub(r'</?b>','',story))[:950] if story and not attached else label+row['name'][:75])
                    c.execute('insert or ignore into notification_photo_outbox(day,period,chat,user_id,photo,caption) values(?,?,?,?,?,?)',
                              (s['today'](),period,json.dumps(chat),row['user_id'],photo,caption))
                    attached=True
                if not attached:text_only.append(chat)
        if story and text_only:broadcast(story,chats=text_only)
        retry_photos()

    def publish_to_all(msg, body):
        """Send a teacher's message or Telegram media to every enrolled user and the adult chat."""
        with s['conn']() as c:
            recipients=[r['id'] for r in c.execute('select id from users order by id')]
        if s['GROUP']:recipients.append(s['GROUP'])
        media=bool(msg.get('photo') or msg.get('document') or msg.get('video'))
        results=[]
        for chat in recipients:
            try:
                result=(s['send_attachment'](chat,msg,'TIMECODE / '+body)
                        if media else s['send'](chat,'📢 <b>TIMECODE</b>\n'+s['esc'](body)))
            except Exception:
                result={}
            results.append(bool(result and result.get('ok')))
        return sum(results),len(recipients)-sum(results)

    def make_daily(kind):
        if kind!='tip':return original_make_daily(kind)
        base=s['fallback_content']('tip')
        if not s['AI_KEY'] or not s['creative_enabled']():return base
        with s['conn']() as c:
            previous=[r['title'] for r in c.execute("select title from daily_content where kind='tip' order by day desc limit 12")]
        theme=s['TIP_TOPICS'][(s['now']().date()-dt.date(2026,1,1)).days%len(s['TIP_TOPICS'])]
        sites=('studiobinder.com','blog.frame.io','nofilmschool.com','poynter.org','youtube.com')
        query=s['ai_json']('Ты редактор TIMECODE. Ежедневно находишь ОДИН практический киношный или блогерский лайфхак, который школьник сможет повторить с телефоном или перед камерой. '
                           'Сегодня твоя область: '+theme+'. Составь точную англоязычную поисковую фразу для практической инструкции в профессиональном источнике. '
                           'Не ищи обзор фильма или сериала, определение термина, оборудование для профессиональной студии или общие рассуждения. Не повторяй последние темы. JSON {"query":"..."}.',
                           json.dumps({'previous':previous,'sites':sites,'theme':theme},ensure_ascii=False),140) or {}
        topic=str(query.get('query','')).strip()[:120]
        if not topic:return base
        found=s['industry_search'](topic,sites)
        if not found:return base
        prompt=('Ты остроумный автор ежедневного лайфхака TIMECODE для школьников 12–17 лет. '
                'Каждый день находишь полезный киношный или блогерский приём и перерабатываешь его в короткий живой текст. '
                'Сегодняшняя область: '+theme+'. Из фрагмента источника выбери ОДНО действие, которое школьник сможет попробовать сегодня телефоном или перед камерой. '
                'Заголовок 2–5 слов. В первой короткой фразе скажи, что конкретно сделать: как поставить свет или камеру, что сказать, записать, снять или изменить в тексте. '
                'Во второй объясни, что получится и почему. Лёгкий остроумный поворот приветствуется, если не мешает инструкции; не шути над ребёнком и не добавляй шутку ради шутки. '
                '2–3 коротких предложения, максимум 260 символов. Должно быть понятно без перехода по ссылке. '
                'Никаких отсылок к фильмам и сериалам, имён актёров, брендов и необъяснённого профессионального жаргона. '
                'Не добавляй фактов, которых нет в источнике, не копируй его дословно. JSON {"title":"...","body":"..."}.')
        drafted=s['ai_json'](prompt,json.dumps(found,ensure_ascii=False),360) or {}
        title=str(drafted.get('title','')).strip();body=str(drafted.get('body','')).strip()
        action=re.search(r'\b(сними|запиши|поставь|поверни|подойди|проверь|послушай|задай|оставь|выбери|сравни|включи|попробуй|сделай|подожди|начни|держи|покажи|спроси|подними|напиши|размести|передвинь|убери|скажи|отодвинь|освети|встань|направь|приблизь|найди|обрежь|разверни|останови|сократи|переставь|повтори|попроси|говори)\b',body,re.I)
        if 5<=len(title)<=45 and 55<=len(body)<=260 and action and len(re.findall(r'[.!?](?:\s|$)',body))>=2 and not any(c in body for c in '«»"'):
            checked=s['ai_json']('Ты выпускающий редактор лайфхаков для школьников. Проверь строго: ok=true только если есть конкретное действие, которое можно повторить сегодня телефоном или перед камерой, объяснён ощутимый результат, приём подтверждается фрагментом источника, нет непонятных отсылок к фильмам или жаргона, а юмор не мешает инструкции. Иначе ok=false. Ответ JSON {"ok":true}.',json.dumps({'source':found['snippet'],'title':title,'body':body},ensure_ascii=False),100)
            if (checked or {}).get('ok') is True:return {'title':title,'body':body,'mode':'text','source':found['url']}
        return base

    original_make_daily=s['make_daily']

    def day_label():
        t=s['now']()
        months=('января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря')
        return str(t.day)+' '+months[t.month-1]

    def morning():
        weekend=s['now']().weekday()>=5
        at='09:00' if weekend else '07:30'
        close='09:50' if weekend else '09:00'
        editorial=('Ты Кими, ведущий школьного медиацентра TIMECODE. Напиши одну короткую '
                   'остроумную утреннюю реплику для школьников и взрослых. Представь, что '
                   'заглянул в шуточный гороскоп съёмочной группы: звёзды обещают отличный '
                   'день для конкретного смешного творческого действия. Это шутка, '
                   'не настоящий прогноз. Одна мысль, не больше 200 знаков; без '
                   'банальностей, предсказаний о личной жизни и упоминания вымышленных '
                   'ответов детей. Верни JSON {"text":"..."}.')
        created=s['ai_json'](editorial,json.dumps({'date':day_label(),'weekend':weekend},ensure_ascii=False),140) if s['AI_KEY'] else None
        line=str((created or {}).get('text','')).strip()
        if not 25<=len(line)<=220 or re.search(r'<[^>]+>',line):
            line='Заглянул в гороскоп съёмочной группы: звёзды обещают удачный день тому, кто наконец нажмёт REC, а не будет репетировать на словах.'
        text=('☀️ <b>'+at+' / ДОБРОЕ УТРО'+(' ВЫХОДНОГО ДНЯ' if weekend else '')+'!</b>\n'
              '<b>'+day_label()+'.</b> '+s['esc'](line)+'\n\n'
              'Впереди наша перекличка. Расскажи, как проснулся и что тебя сегодня волнует. '
              'Пришли фото своего утра, если хочешь: в 10:00 соберу ваши ответы и кадры '
              'в один рассказ. В 15:00 вернусь с лайфхаком. Ответы принимаю до '+close+'.')
        keyboard=[[{'text':'😌 Выспался','callback_data':'morning:sleep:Выспался'},
                   {'text':'😐 Так себе','callback_data':'morning:sleep:Так себе'}],
                  [{'text':'🥱 Мало спал','callback_data':'morning:sleep:Мало спал'},
                   {'text':'Пропустить','callback_data':'morning:skip'}]]
        for uid in audience():s['send'](uid,text,keyboard)
        if s['GROUP']:s['send'](s['GROUP'],text)

    def evening():
        original_evening()
        if s['GROUP']:
            s['send'](s['GROUP'],'🌙 <b>18:00 / ВЕЧЕРНЯЯ ПЕРЕКЛИЧКА</b>\nКак прошёл день? Ответить можно лично боту до 20:00.')

    def reminder(period):
        if period=='am':
            close='09:50' if s['now']().weekday()>=5 else '09:00'
            at='09:30' if s['now']().weekday()>=5 else '08:30'
            with s['conn']() as c:
                users=c.execute("select u.id from users u left join morning_checkins m on m.user_id=u.id and m.day=? where u.enabled=1 and (m.step is null or m.step not in ('done','closed'))",(s['today'](),)).fetchall()
            message='⏱ <b>'+at+' / УТРЕННЯЯ ПЕРЕКЛИЧКА</b>\nЕщё можно рассказать о своём утре и прислать фото. Жду до '+close+', в 10:00 соберу истории в выпуск.'
            for u in users:s['send'](u['id'],message,[[{'text':'Ответить боту','callback_data':'morning:start'}]])
            if s['GROUP']:s['send'](s['GROUP'],message)
            return
        original_reminder(period)
        if s['GROUP']:
            s['send'](s['GROUP'],'⏱ <b>19:00 / ВЕЧЕР</b>\nЕсли хотел ответить боту — приём до 20:00.')

    def digest(period):
        morning=period!='pm'
        with s['conn']() as c:
            if morning:
                rows=c.execute("select u.id user_id,u.name,m.sleep,m.mood,m.important,m.photo from morning_checkins m join users u on u.id=m.user_id where m.day=? and m.step='done' and m.mood!='' order by u.name",(s['today'](),)).fetchall()
            else:
                rows=c.execute("select u.id user_id,u.name,e.mood,e.highlight,e.satisfied,e.photo from evening_checkins e join users u on u.id=e.user_id where e.day=? and e.step='done' and e.mood!='' order by u.name",(s['today'](),)).fetchall()
        body=editorial_voice.story(s,rows,morning)
        label=('☀️ <b>10:00 / ИСТОРИИ ЭТОГО УТРА</b>\n\n' if morning else '🌙 <b>20:30 / КАК ПРОШЁЛ ДЕНЬ</b>\n\n')
        broadcast_checkin_photos(rows,'am' if morning else 'pm',label+s['esc'](body))

    def tip():
        item = s['daily_content']('tip', True)
        source = '\n<a href="' + html.escape(item['source'], quote=True) + '">Откуда идея ↗</a>' if item['source'] else ''
        broadcast('⏱ <b>15:00 / ПРИЁМ ДНЯ</b>\n\n<b>' + s['esc'](item['title']) + '</b>\n' + s['esc'](item['body']) + source,
                  [[{'text':'Открыть лайфхак в TIMECODE ↗','url':s['BASE']+'/?view=tip'}]])

    def mission():
        if not s['BOTNAME']: return
        item = s['daily_content']('mission', True)
        broadcast('🎬 <b>СТРАННОЕ ЗАДАНИЕ</b>\n\n<b>' + s['esc'](item['title']) + '</b>\n' + s['esc'](item['body']),
                  [[{'text':'Ответить боту ↗','url':'https://t.me/'+s['BOTNAME']+'?start=mission'}]])

    def instant_photo():
        original_instant_photo()

    def photos_digest():
        with s['conn']() as c:
            rows = c.execute("select m.user_id,m.photo,m.comment,u.name from missions m join users u on m.user_id=u.id where m.day=? and m.kind='instant' and m.published=1", (s['today'](),)).fetchall()
        pictures=[]
        for r in rows:
            if not r['photo']: continue
            comment = r['comment'] or s['photo_comment'](r['photo'])
            if comment and not r['comment']:
                with s['conn']() as c: c.execute("update missions set comment=? where user_id=? and day=? and kind='instant'",(comment,r['user_id'],s['today']()))
            pictures.append({'photo':r['photo'],'name':r['name'],'comment':comment})
        for chat in destinations():
            for start in range(0,len(pictures),10):
                batch=pictures[start:start+10]
                if len(batch)>1:
                    media=[{'type':'photo','media':r['photo'],'caption':('📸 '+r['name']+('\n'+r['comment'] if r['comment'] else ''))[:850]} for r in batch]
                    s['api']('sendMediaGroup',{'chat_id':chat,'media':media})
                elif batch:
                    r=batch[0];s['api']('sendPhoto',{'chat_id':chat,'photo':r['photo'],'caption':'📸 '+r['name']+('\n'+r['comment'] if r['comment'] else '')})

    def run_slot(key, fn):
        if s['claim'](key,s['today']()):
            try: fn()
            except Exception as e:
                with s['conn']() as c:c.execute('delete from sent where slot=? and day=?',(key,s['today']()))
                print('Slot failed:',key,str(e)[:200],flush=True)

    def weekly():
        weekstart=(s['now']().date()-dt.timedelta(days=6)).isoformat()
        with s['conn']() as c:
            rows=c.execute("select u.name,(select count(*) from morning_checkins m where m.user_id=u.id and m.day>=? and m.step='done') morning,(select count(*) from evening_checkins e where e.user_id=u.id and e.day>=? and e.step='done') evening from users u",(weekstart,weekstart)).fetchall()
        people=[r for r in rows if r['morning']+r['evening']>0]
        if people:
            body='\n'.join('• '+s['esc'](r['name'])+': утром — '+str(r['morning'])+', вечером — '+str(r['evening'])+'.' for r in people[:12])
            broadcast('🎞 <b>ТИТРЫ НЕДЕЛИ</b>\n\n'+body+'\n\nЭто перекличка, не оценки.')

    def class_reminders():
        t=s['now'](); day=t.date().isoformat()
        with s['conn']() as c:
            overrides=c.execute('select * from overrides where day=?',(day,)).fetchall()
            regular=c.execute('select * from lessons where weekday=? and enabled=1',(t.weekday(),)).fetchall()
        if t.weekday()==5 and t.hour==9 and t.minute==0 and s['claim']('saturday-classes',day):
            lines=[]
            for lab in ('kids','media'):
                event=next((o for o in overrides if o['lab']==lab),None)
                if event is None:event=next((r for r in regular if r['lab']==lab),None)
                if event and (not 'cancelled' in event.keys() or not event['cancelled']):
                    lines.append(('Kids Lab' if lab=='kids' else 'Media Lab')+' — '+s['esc'](event['start']))
            if lines:
                broadcast('🎬 <b>Сегодня занятия!</b>\nПомните? '+'; '.join(lines)+'.\nДмитрий Витальевич вас ждёт. До встречи!')
        for item in list(overrides)+list(regular):
            lab=item['lab']; override=next((o for o in overrides if o['lab']==lab),None)
            if 'weekday' in item.keys() and override: continue
            event=item
            try: start=dt.datetime.combine(t.date(),dt.time.fromisoformat(event['start']),s['TZ'])
            except ValueError: continue
            if 0 <= (start-t).total_seconds() <= 6000 and s['claim']('lesson:'+lab+':'+event['start'],day):
                if 'cancelled' in event.keys() and event['cancelled']: continue
                label='Kids Lab' if lab=='kids' else 'Media Lab'
                message='🎬 <b>СЕГОДНЯ ЗАНЯТИЕ / '+label+'</b>\n'+s['esc'](event['start'])+' · '+s['esc'](event['title'])+'\n'+s['esc'](event['place'])+'\n\nДмитрий Витальевич ждёт. Камеры зарядить; себя — по возможности тоже.'
                broadcast(message)

    s.update({'morning':morning,'evening':evening,'reminder':reminder,'digest':digest,'evening_digest':lambda:digest('pm'),'tip':tip,'mission':mission,'instant_photo':instant_photo,'photos_digest':photos_digest,'run_slot':run_slot,'weekly':weekly,'class_reminders':class_reminders,'publish_to_all':publish_to_all,'make_daily':make_daily,'retry_notifications':retry_notifications,'broadcast_checkin_photos':broadcast_checkin_photos})
