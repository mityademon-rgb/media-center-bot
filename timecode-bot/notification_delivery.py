"""The same daily broadcasts go to every subscriber and the connected adult chat."""
import datetime as dt
import html
import json
import re


def install(s):
    original_evening=s['evening']
    def audience():
        with s['conn']() as c:
            return [r['id'] for r in c.execute('select id from users where enabled=1')]

    def destinations():
        return list(dict.fromkeys(audience() + ([s['GROUP']] if s['GROUP'] else [])))

    def broadcast(message, keyboard=None):
        for chat in destinations():
            s['send'](chat, message, keyboard)

    def broadcast_checkin_photos(rows):
        photos=[{'photo':r['photo'],'name':r['name']} for r in rows if r['photo']]
        for chat in destinations():
            for start in range(0,len(photos),10):
                batch=photos[start:start+10]
                if len(batch)>1:
                    media=[{'type':'photo','media':r['photo'],'caption':'📸 Кадр от '+r['name'][:75]} for r in batch]
                    s['api']('sendMediaGroup',{'chat_id':chat,'media':media})
                elif batch:
                    s['api']('sendPhoto',{'chat_id':chat,'photo':batch[0]['photo'],'caption':'📸 Кадр от '+batch[0]['name'][:75]})

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
                rows=c.execute("select u.name,m.sleep,m.mood,m.important,m.photo from morning_checkins m join users u on u.id=m.user_id where m.day=? and m.step='done' and m.mood!='' order by u.name",(s['today'](),)).fetchall()
            else:
                rows=c.execute("select u.name,e.mood,e.highlight,e.satisfied,e.photo from evening_checkins e join users u on u.id=e.user_id where e.day=? and e.step='done' and e.mood!='' order by u.name",(s['today'](),)).fetchall()
        facts=([{'name':r['name'],'sleep':r['sleep'],'mood':r['mood'],'words':r['important'][:150]} for r in rows[:12]] if morning else
               [{'name':r['name'],'mood':r['mood'],'words':r['highlight'][:150],'satisfied':r['satisfied']} for r in rows[:12]])
        story_prompt=('Ты Кими, ведущий школьного медиацентра TIMECODE. Ты пишешь ОДИН связный мини-рассказ от первого лица бота по реальным ответам детей, а не статистику. '
                      'Сначала интересный заход, затем вплети конкретные ответы участников с именами в общую историю, свяжи их переходами и закончи живой фразой. '
                      'История должна двигаться, как маленькая редакционная колонка: никакого списка, пунктов, сухого пересказа анкет, подсчётов, повторения вопроса и заголовков внутри текста. '
                      'Используй только переданные факты, не дописывай события, причины настроения, оценки, слова детей или содержание фото. '
                      'Шути над обстоятельствами и собственной ролью ведущего, но не над детьми; не приписывай детям негативных поступков. '
                      +('Сегодня утренний выпуск. В финале ОБЯЗАТЕЛЬНО пообещай вернуться с простым лайфхаком в 15:00. ' if morning else
                        'Сегодня вечерний выпуск. Закончи пожеланием хорошего вечера или выходных, если пятница. ')+
                      'Текст 300–650 знаков, без HTML и Markdown. Верни JSON {"text":"..."}.')
        drafted=s['ai_json'](story_prompt,json.dumps({'date':day_label(),'weekday':s['now']().weekday(),'answers':facts},ensure_ascii=False),500) if rows and s['AI_KEY'] else None
        generated=str((drafted or {}).get('text','')).strip()
        named=[r['name'] for r in rows if (r['important'] if morning else r['highlight']) and (r['important'] if morning else r['highlight'])!='Не было']
        bad_format=re.search(r'<[^>]+>|(?:^|\n)\s*(?:[•*\-]|\d+[.)])|(?:На связи|Выспались:|Настроение:|Довольны днём:)',generated,re.I)
        if generated and 180<=len(generated)<=850 and not bad_format and all(name in generated for name in named[:5]):
            body=generated
            if morning and '15:00' not in body:body+=' В 15:00 вернусь с лайфхаком.'
        elif rows:
            if morning:
                opening='Сегодня утро у всех началось по-своему. '
                details=[r['name']+' поделился(ась) планом: '+r['important'][:120].rstrip(' .!')+'.' for r in rows if r['important']]
                if not details:details=[r['name']+' рассказал(а), что настроение сегодня '+r['mood'].lower()+'.' for r in rows[:4]]
                ending=' Спасибо за откровенность и за кадры утра. В 15:00 вернусь с простым лайфхаком.'
            else:
                opening='Вечер собрал сегодня несколько очень разных историй. '
                details=[r['name']+' рассказал(а): '+r['highlight'][:120].rstrip(' .!')+'.' for r in rows if r['highlight'] and r['highlight']!='Не было']
                if not details:details=['Ребята поделились настроением дня — и это уже повод закончить его вместе.']
                ending=' Спасибо всем, кто был на связи. '+('Хороших выходных!' if s['now']().weekday()==4 else 'Хорошего вечера!')
            body=opening+' '.join(details[:6])+ending
        else:
            body=('Утром в редакции пока тихо. Даже хорошие истории иногда начинаются с паузы. В 15:00 вернусь с лайфхаком.' if morning else
                  'Сегодня у микрофона было тихо. Ничего страшного: иногда лучший кадр остаётся за экраном. Хорошего вечера!')
        label=('☀️ <b>10:00 / ИСТОРИИ ЭТОГО УТРА</b>\n\n' if morning else '🌙 <b>20:30 / КАК ПРОШЁЛ ДЕНЬ</b>\n\n')
        broadcast(label+s['esc'](body))
        broadcast_checkin_photos(rows)

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
