"""The same daily broadcasts go to every subscriber and the connected adult chat."""
import datetime as dt
import html


def install(s):
    original_morning=s['morning']
    original_evening=s['evening']
    original_reminder=s['reminder']
    def audience():
        with s['conn']() as c:
            return [r['id'] for r in c.execute('select id from users where enabled=1')]

    def destinations():
        return audience() + ([s['GROUP']] if s['GROUP'] else [])

    def broadcast(message, keyboard=None):
        for chat in destinations():
            s['send'](chat, message, keyboard)

    def morning():
        original_morning()
        if s['GROUP']:
            s['send'](s['GROUP'],'☀️ <b>07:30 / ДОБРОЕ УТРО!</b>\nКак спалось, как дела и что сегодня важного? Ответить можно лично боту до 09:00.')

    def evening():
        original_evening()
        if s['GROUP']:
            s['send'](s['GROUP'],'🌙 <b>18:00 / ВЕЧЕРНЯЯ ПЕРЕКЛИЧКА</b>\nКак прошёл день? Ответить можно лично боту до 20:00.')

    def reminder(period):
        original_reminder(period)
        if s['GROUP']:
            when='08:30 / УТРО' if period=='am' else '19:00 / ВЕЧЕР'
            end='09:00' if period=='am' else '20:00'
            s['send'](s['GROUP'],'⏱ <b>'+when+'</b>\nЕсли хотел ответить боту — приём до '+end+'.')

    def digest(period):
        if period == 'pm':
            with s['conn']() as c:
                rows = c.execute("select u.name,e.mood,e.highlight,e.satisfied from evening_checkins e join users u on u.id=e.user_id where e.day=? and e.step='done' and e.mood!='' order by u.name", (s['today'](),)).fetchall()
            if rows:
                counts = {k: sum(r['mood'] == k for r in rows) for k in ('Хороший', 'Обычный', 'Сложный')}
                body = f"На связи {len(rows)}. Хороший день: {counts['Хороший']}, обычный: {counts['Обычный']}, непростой: {counts['Сложный']}. Довольны днём: {sum(r['satisfied'] == 'Да' for r in rows)}."
                highlights = ['• <b>' + s['esc'](r['name']) + '</b>: ' + s['esc'](r['highlight'][:140]) for r in rows if r['highlight'] and r['highlight'] != 'Не было']
                if highlights: body += '\n' + '\n'.join(highlights[:10])
            else: body = 'Сегодня без ответов. Завтра будет новый день.'
            broadcast('🌙 <b>20:30 / КАК ПРОШЁЛ ДЕНЬ</b>\n\n' + body)
            return
        with s['conn']() as c:
            rows = c.execute("select u.name,m.sleep,m.mood,m.important from morning_checkins m join users u on u.id=m.user_id where m.day=? and m.step='done' and m.mood!='' order by u.name", (s['today'](),)).fetchall()
        if rows:
            facts = [{'name':r['name'],'sleep':r['sleep'],'mood':r['mood'],'plans':r['important'][:140]} for r in rows]
            generated = s['ai_digest']('утро', facts)
            body = s['esc'](generated) if generated else '\n'.join('• <b>' + s['esc'](r['name']) + '</b>: ' + s['esc'](r['mood'].lower()) + ', ' + s['esc'](r['sleep'].lower()) + (('; ' + s['esc'](r['important'][:130])) if r['important'] else '') for r in rows[:12])
            body = 'На связи ' + str(len(rows)) + '\n' + body
        else: body = 'Пока в эфире тихо. Ждём следующего выпуска.'
        broadcast('☀️ <b>10:00 / УТРЕННЯЯ СВОДКА TIMECODE</b>\n\n' + body)

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
        if not s['BOTNAME']: return
        with s['conn']() as c: c.execute("update users set stage='instant' where enabled=1 and stage=''")
        broadcast('📸 <b>МГНОВЕННОЕ ФОТО</b>\nСфоткай то, что прямо сейчас перед тобой. Один кадр, без подготовки. Присылай до 20:00 — вечером соберём общую подборку. Если в кадре люди, спроси их согласия.',
                  [[{'text':'Отправить кадр боту ↗','url':'https://t.me/'+s['BOTNAME']+'?start=instant'}]])

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
            except Exception as e: print('Slot failed:',key,str(e)[:200],flush=True)

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
        for item in list(overrides)+list(regular):
            lab=item['lab']; override=next((o for o in overrides if o['lab']==lab),None)
            if 'weekday' in item.keys() and override: continue
            event=override if 'weekday' in item.keys() else item
            try: start=dt.datetime.combine(t.date(),dt.time.fromisoformat(event['start']),s['TZ'])
            except ValueError: continue
            if 0 <= (start-t).total_seconds() <= 6000 and s['claim']('lesson:'+lab+':'+event['start'],day):
                if 'cancelled' in event.keys() and event['cancelled']: continue
                label='Kids Lab' if lab=='kids' else 'Media Lab'
                message='🎬 <b>СЕГОДНЯ ЗАНЯТИЕ / '+label+'</b>\n'+s['esc'](event['start'])+' · '+s['esc'](event['title'])+'\n'+s['esc'](event['place'])+'\n\nДмитрий Витальевич ждёт. Камеры зарядить; себя — по возможности тоже.'
                broadcast(message)

    s.update({'morning':morning,'evening':evening,'reminder':reminder,'digest':digest,'evening_digest':lambda:digest('pm'),'tip':tip,'mission':mission,'instant_photo':instant_photo,'photos_digest':photos_digest,'run_slot':run_slot,'weekly':weekly,'class_reminders':class_reminders})
