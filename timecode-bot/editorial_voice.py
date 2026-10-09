"""Conversational TIMECODE posts grounded in participants' actual replies."""
import hashlib
import json
import re


def photo_caption(name, comment, day):
    name=str(name)[:80]
    intros=(
        f'Друзья, вот кадр от {name}. Это то, что сейчас перед камерой нашего автора.',
        f'{name} прислал кадр своего дня. Показываю вам: у каждого сейчас своя сцена, и вот одна из них.',
        f'В нашем сегодняшнем эфире — фотография от {name}. Посмотрим, что сейчас происходит по ту сторону его камеры.',
    )
    index=int(hashlib.sha256((day+name).encode()).hexdigest()[:8],16)%len(intros)
    comment=' '.join(str(comment or '').split())
    if re.search(r'не (?:могу|удалось|получилось)|не удалось|не (?:вижу|разобрал|распозна)|невозможно (?:оценить|рассмотр)|недоступ|вслепую|как (?:ии|модель)|на изображении нет',comment,re.I):
        comment=''
    if not comment:
        return (f'КАДР ДНЯ · {name}\n\n'+intros[index]+
                ' Рассмотрите снимок: куда первым делом падает ваш взгляд? Интересно, заметили бы вы этот момент, проходя мимо.')
    return f'КАДР ДНЯ · {name}\n\n'+intros[index]+' '+comment[:600]


def fallback_story(rows, morning, games=None):
    games=games or []
    if not rows and games:
        names=list(dict.fromkeys(g['name'] for g in games))
        return ('Друзья, сегодня со мной поиграли '+', '.join(names)+'. Спасибо, что пробовали свои силы и разбирали решения после каждого вопроса. '
                'Все молодцы: вы потренировались принимать решения на съёмке. Там, где ответы пока не сошлись, есть конкретная задача для следующей попытки — личные подсказки я уже отправил. Хорошего вечера!')
    if not rows:
        return ('Доброе утро, друзья. Сегодня ответов пока нет, поэтому оставлю микрофон открытым: если захочется рассказать, как идёт день, пишите мне здесь. В 15:00 вернусь с лайфхаком — будет что попробовать на съёмке.' if morning else
                'Друзья, сегодня ответов на вечернюю перекличку пока нет. Если захочется рассказать, что запомнилось, я на связи в этом чате. А пока желаю спокойного вечера — завтра снова соберём наши истории.')
    parts=[]
    for row in rows[:3]:
        name=row['name'][:40]
        words=(row['important'] if morning else row['highlight']).strip()
        if words and words not in ('Не было','Пропустить'):
            parts.append(name+' поделился '+('планами и мыслями на сегодня' if morning else 'тем, что запомнилось за день')+': «'+words[:65].rstrip(' .')+'».')
        else:
            mood=row['mood'].lower()
            parts.append(name+' отметил '+('утреннее настроение' if morning else 'настроение дня')+': '+mood+'.')
    beginning=('Друзья, прочитал ваши утренние ответы. У каждого свой старт, и мне хочется собрать эти истории в одном выпуске. ' if morning else
               'Друзья, прочитал ваши ответы и собираю сегодняшний день по вашим историям. Вот чем вы решили поделиться. ')
    ending=(' Спасибо, что выходите на связь. Если захочется продолжить разговор, пишите сюда. В 15:00 вернусь с лайфхаком.' if morning else
            ' Спасибо, что рассказали об этом. Если за коротким ответом осталась целая история, я здесь и готов её выслушать. Хорошего вечера!')
    if games:
        names=list(dict.fromkeys(g['name'] for g in games))
        ending=' Со мной сегодня поиграли '+', '.join(names)+'. Все молодцы: попробовали свои силы и разобрали решения. Личные подсказки пригодятся на следующей съёмке. Хорошего вечера!'
    return beginning+' '.join(parts)+ending


def story(s, rows, morning):
    kind='digest-story-am' if morning else 'digest-story-pm'
    with s['conn']() as c:
        cached=c.execute('select body from daily_content where day=? and kind=?',(s['today'](),kind)).fetchone()
    if cached:return cached['body']
    weekday_name=('понедельник','вторник','среда','четверг','пятница','суббота','воскресенье')[s['now']().weekday()]
    calendar={'date':s['today'](),'weekday_name':weekday_name}
    facts=[]
    games=[]
    if not morning:
        with s['conn']() as c:
            if c.execute("select 1 from sqlite_master where type='table' and name='chat_game_runs'").fetchone():
                games=[{k:r[k] for k in ('name','topic','step','score')} for r in c.execute("select u.name,g.topic,g.step,g.score,g.missed from chat_game_runs g join users u on u.id=g.user_id where g.day=? and g.step>0 order by u.name",(s['today']().replace('-',''),))]
    for r in rows[:12]:
        item={'name':r['name'],'mood':r['mood'],'words':r['important'] if morning else r['highlight']}
        item['sleep' if morning else 'satisfied']=r['sleep'] if morning else r['satisfied']
        if 'photo' in r.keys() and r['photo']:
            item['photo_received']=True
            with s['conn']() as c:
                if c.execute("select 1 from sqlite_master where type='table' and name='photo_hunts'").fetchone():
                    photo_info=c.execute('select task,comment from photo_hunts where user_id=? and day=? and period=?',(r['user_id'],s['today'](),'am' if morning else 'pm')).fetchone()
                    if photo_info:
                        item['photo_task']=photo_info['task']
                        item['photo_observation']=photo_info['comment']
        facts.append(item)
    prompt=(
        'Ты TIMECODE, бот медиацентра. Разговариваешь с участниками как живой ведущий: на равных, тепло, с лёгкой иронией и без сюсюканья. '
        'Сегодня '+s['today']()+', '+weekday_name+'. Это точный календарь по Москве. Не называй сегодня другим днём недели; ответы о вчерашних событиях не меняют текущую дату. '
        'Напиши весёлый цельный рассказ от своего имени по выбранным персонажам дня, добровольным репликам и фотоохоте. Состояние «зомби», «ленивец», «монтажный брак», «1%» — игровые самоописания, а не диагнозы или оценка ученика. Не протокол, не рубленые реплики, не список: Живой короткий рассказ на 500–1400 знаков, 2–3 небольших абзаца. Не подгоняй его под одинаковое число предложений. '
        'Начни с самой интересной реальной детали дня, чтобы захотелось читать дальше. Разговаривай от первого лица: замечай, сопоставляй, удивляйся, задай один уместный вопрос. Свяжи 2–4 реальных ответа с именами в небольшой рассказ; не проходи по каждому участнику по очереди. Не начинай ежедневно с «прочитал ваши ответы». '
        'Цитируй только если это помогает истории; не повторяй перед каждым именем «пишет», «отмечает», «вспоминает». Не подсчитывай настроение и участников. '
        'У тебя свой характер: умный, ироничный, немного ворчливый редактор, который любит свою компанию. Замечай конкретную находку, свет или ракурс. Учим через развлечение: никаких оценок, отчёта перед учителем и морали. Одна точная шутка по реальной детали лучше пяти шуток про микрофон и эфир. Не высмеивай детей, не морализируй, не заканчивай дежурным «спасибо за участие». '
        'Ты прочитал ответы, но не видел событий. Не придумывай обстоятельства, связи между людьми, привычки, причины настроения, диалоги и содержание фотографий. '
        'Не объявляй настроение всей группы одинаковым, если ответы разные. Имена сохраняй как в исходных данных. Не начинай с «В редакции», не злоупотребляй метафорами про титры и общий эфир. Если есть photo_observation, свяжи видимые детали кадров с выбранными персонажами. Если наблюдение пустое, назови автора и факт полученного фото, но не выдумывай предмет, свет и композицию. Фото прикрепит система. '
        'Если есть game_participants, вплети в вечерний рассказ, кто сегодня со мной играл. Имена назови и отметь реальный результат; не заканчивай дежурным «все молодцы». '
        'Игровые ответы и ошибки остаются личными. В рассказе допустимы только имена, факт участия и итоговый счёт. Не цитируй выбранные варианты и не рассказывай публично, в чём ошибся участник. '
        +('Это утро. Последняя фраза: вернусь с лайфхаком в 15:00.' if morning else 'Это вечер. Заверши пожеланием хорошего вечера, а в пятницу — хороших выходных.')+
        ' Без заголовка, HTML, Markdown и эмодзи. Верни JSON {"text":"..."}.'
    )
    result=s['ai_json'](prompt,json.dumps({'date':s['today'](),'weekday_name':weekday_name,'answers':facts,'game_participants':games},ensure_ascii=False),750) if (facts or games) and s['AI_KEY'] else None
    candidate=str((result or {}).get('text','')).strip()
    if candidate:
        checked=s['ai_json']('Ты фактчекер, не переписывай авторский голос. Проверь calendar и реальные answers: нет ли придуманных событий, неверного сегодняшнего дня недели, приписанных людям мотивов, публичного разбора игровых ответов или ошибок. Стиль и лёгкую иронию не запрещай. Верни JSON {"ok":true,"reason":""}.',
                             json.dumps({'calendar':calendar,'answers':facts,'game_participants':games,'draft':candidate},ensure_ascii=False),220) or {}
        if checked.get('ok') is not True:
            revised=s['ai_json'](prompt+' Исправь только замечания фактчекера, сохрани разговорный авторский голос.',json.dumps({'calendar':calendar,'answers':facts,'game_participants':games,'draft':candidate,'editor_note':checked.get('reason','Проверь факты и календарь')},ensure_ascii=False),1000) or {}
            candidate=str(revised.get('text','')).strip()
            checked=s['ai_json']('Проверь только факты и calendar: нет выдуманных событий, неверного сегодняшнего дня и публичных игровых ответов. JSON {"ok":true}.',json.dumps({'calendar':calendar,'answers':facts,'game_participants':games,'draft':candidate},ensure_ascii=False),180) or {}
            if checked.get('ok') is not True:candidate=''
    sentences=len(re.findall(r'[.!?](?:\s|$)',candidate))
    bad=re.search(r'<[^>]+>|(?:^|\n)\s*(?:[•*]|\d+[.)])|не (?:смог|удалось).*?(?:обработ|разобра)|На связи \d',candidate,re.I)
    if not (200<=len(candidate)<=1600 and sentences>=3 and not bad):candidate=fallback_story(rows,morning,games)
    if morning and '15:00' not in candidate:candidate+=' В 15:00 вернусь с лайфхаком.'
    with s['conn']() as c:
        c.execute('insert or ignore into daily_content(day,kind,title,body) values(?,?,?,?)',(s['today'](),kind,'Истории переклички',candidate))
    return candidate
