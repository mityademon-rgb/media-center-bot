"""The same daily broadcasts go to every subscriber and the connected adult chat."""
import datetime as dt
import html
import json
import re


def install(s):
    original_morning=s['morning']
    original_evening=s['evening']
    original_reminder=s['reminder']
    def audience():
        with s['conn']() as c:
            return [r['id'] for r in c.execute('select id from users where enabled=1')]

    def destinations():
        return list(dict.fromkeys(audience() + ([s['GROUP']] if s['GROUP'] else [])))

    def broadcast(message, keyboard=None):
        for chat in destinations():
            s['send'](chat, message, keyboard)

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
        sites=s['SOURCE_SETS'][(s['now']().date()-dt.date(2026,1,1)).days%len(s['SOURCE_SETS'])]
        query=s['ai_json']('Ты ищешь новый практический приём для школьного медиацентра: '
                           'съёмка телефоном, запись звука, интервью, сюжет для ТВ или простой монтаж. '
                           'Выбери тему сам, избегай уже опубликованных. Составь конкретный поисковый запрос '
                           'на английском. JSON {"query":"..."}.',
                           json.dumps({'previous':previous,'sites':sites},ensure_ascii=False),140) or {}
        topic=str(query.get('query','')).strip()[:120]
        if not topic:return base
        found=s['industry_search'](topic,sites)
        if not found:return base
        prompt=('Ты автор коротких советов TIMECODE для школьников 12–17 лет, которые снимают '
                'на телефон, делают интервью и сюжеты. На основе найденного материала '
                'сам выбери ОДИН реально применимый приём и расскажи его простыми словами. '
                'Заголовок 2–5 слов. Текст 2–3 коротких предложения: что конкретно сделать '
                'и что это даст в кадре, звуке или истории. Лёгкая улыбка допустима. '
                'Никаких имён актёров, фильмов, сериалов, брендов, внутреннего жаргона, '
                'необъяснённых терминов и намёков, понятных только знатокам кино. '
                'Не добавляй фактов, которых нет в найденном материале. '
                'JSON {"title":"...","body":"..."}.')
        drafted=s['ai_json'](prompt,json.dumps(found,ensure_ascii=False),300) or {}
        title=str(drafted.get('title','')).strip();body=str(drafted.get('body','')).strip()
        action=re.search(r'\b(сними|запиши|поставь|поверни|подойди|проверь|послушай|задай|оставь|выбери|сравни|включи|попробуй|сделай|подожди|начни|держи|покажи|спроси|подними)\b',body,re.I)
        if 5<=len(title)<=45 and 55<=len(body)<=260 and action and body.count('.')>=2 and not any(c in body for c in '«»"'):
            return {'title':title,'body':body,'mode':'text','source':found['url']}
        return base

    original_make_daily=s['make_daily']

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
                facts=[{'name':r['name'],'mood':r['mood'],'highlight':r['highlight'][:140],
                        'satisfied':r['satisfied']} for r in rows[:15]]
                weekday=s['now']().weekday()
                prompt=('Напиши короткий остроумный вечерний выпуск школьного медиацентра. '
                        'Говори как добрый редактор, который прочитал ответы ребят: вступление, '
                        'истории конкретных участников, один вывод и финальное пожелание. '
                        'Не делай список, отчёт, подсчёт голосов или табличную сводку. '
                        'Обращайся к участникам по их именам без переименования. '
                        'Цитируй их достижения только по смыслу, не придумывай подробностей '
                        'и не делай выводов об оценках, здоровье, семье или причинах настроения. '
                        'Улыбка над ситуацией допустима, над ребёнком — нет. '
                        'Если сегодня пятница, пожелай хороших выходных; иначе пожелай хорошего вечера. '
                        'Длина 300–650 знаков, обычный текст без разметки. '
                        'JSON {"text":"..."}.')
                draft=s['ai_json'](prompt,json.dumps({'weekday':weekday,'answers':facts},ensure_ascii=False),400) if s['AI_KEY'] else None
                generated=str((draft or {}).get('text','')).strip()
                names=[r['name'] for r in rows if r['highlight'] and r['highlight']!='Не было']
                if generated and 120<=len(generated)<=900 and not re.search(r'<[^>]+>|(?:На связи|Хороший день:|Довольны днём:)',generated,re.I) and all(name in generated for name in names[:4]):
                    body=generated
                else:
                    intro='На мою просьбу рассказать о дне откликнулись самые смелые. Снимаю шляпу.' if len(rows)<4 else 'Сегодня в редакцию прилетели новости от наших героев.'
                    highlights=[r['name']+': «'+r['highlight'][:140].rstrip(' .!')+'». ' for r in rows if r['highlight'] and r['highlight']!='Не было']
                    body=intro+' '+(' '.join(highlights[:5]) if highlights else 'Не каждый день обязан быть премьерой: спасибо всем, кто был на связи.')
                    body+=' На этом съёмочный день закрыт. '+('Хороших выходных!' if weekday==4 else 'Хорошего вечера!')
            else: body='Сегодня в редакции тихо. Даже самые разговорчивые герои иногда уходят за кадр. Хорошего вечера!'
            broadcast('🌙 <b>КАК ПРОШЁЛ ДЕНЬ</b>\n\n' + s['esc'](body))
            return
        with s['conn']() as c:
            rows = c.execute("select u.name,m.sleep,m.mood,m.important from morning_checkins m join users u on u.id=m.user_id where m.day=? and m.step='done' and m.mood!='' order by u.name", (s['today'](),)).fetchall()
        if rows:
            facts = [{'name':r['name'],'sleep':r['sleep'],'mood':r['mood'],'plans':r['important'][:140]} for r in rows[:15]]
            prompt=('Напиши от первого лица короткий утренний выпуск бота TIMECODE для школьного '
                    'медиацентра. Ты прочитал ответы ребят: собери их планы и настроение '
                    'в один живой, добрый, местами остроумный текст со вступлением, '
                    'конкретными историями и финалом. Никаких таблиц, списков, подсчётов '
                    'и формулировки «на связи N». Не выдумывай событий, причин настроения, '
                    'оценок учёбы или слов участников. Не шути над человеком и не раскрывай '
                    'личного сверх того, что он сообщил. Пиши простыми словами как знакомый '
                    'ведущий, 250–650 знаков без HTML. JSON {"text":"..."}.')
            drafted=s['ai_json'](prompt,json.dumps({'answers':facts},ensure_ascii=False),410) if s['AI_KEY'] else None
            generated=str((drafted or {}).get('text','')).strip()
            if generated and 100<=len(generated)<=850 and not re.search(r'<[^>]+>|(?:На связи|Выспались:|Настроение:)',generated,re.I):
                body=generated
            else:
                plans=[r['name']+' сегодня собирается '+r['important'][:120].rstrip(' .!') for r in rows if r['important']]
                body='Утро началось, и у меня уже есть первые новости от ребят. '+(' '.join(p+'.' for p in plans[:5]) if plans else 'Спасибо всем, кто рассказал, как начинается день.')+' Пусть сегодня найдётся хотя бы один хороший кадр.'
        else: body='Утром в редакции пока тихо. Иногда лучший сюжет начинается как раз после паузы. Хорошего дня!'
        broadcast('☀️ <b>УТРЕННИЙ ВЫПУСК TIMECODE</b>\n\n' + s['esc'](body))

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

    s.update({'morning':morning,'evening':evening,'reminder':reminder,'digest':digest,'evening_digest':lambda:digest('pm'),'tip':tip,'mission':mission,'instant_photo':instant_photo,'photos_digest':photos_digest,'run_slot':run_slot,'weekly':weekly,'class_reminders':class_reminders,'publish_to_all':publish_to_all,'make_daily':make_daily})
