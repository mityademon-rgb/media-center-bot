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
    facts=[]
    games=[]
    if not morning:
        with s['conn']() as c:
            if c.execute("select 1 from sqlite_master where type='table' and name='chat_game_runs'").fetchone():
                games=[dict(r) for r in c.execute("select u.name,g.topic,g.step,g.score,g.missed from chat_game_runs g join users u on u.id=g.user_id where g.day=? and g.step>0 order by u.name",(s['today']().replace('-',''),))]
    for r in rows[:12]:
        item={'name':r['name'],'mood':r['mood'],'words':r['important'] if morning else r['highlight']}
        item['sleep' if morning else 'satisfied']=r['sleep'] if morning else r['satisfied']
        facts.append(item)
    prompt=(
        'Ты TIMECODE, бот медиацентра. Разговариваешь с участниками как живой ведущий: на равных, тепло, с лёгкой иронией и без сюсюканья. '
        'Напиши цельный рассказ по ответам переклички от своего имени. Не протокол, не рубленые реплики, не список: 5–7 нормальных связанных предложений в 1–2 абзацах, 450–850 знаков. '
        'Начни с обращения к друзьям и общей мысли, которая действительно следует из ответов. Свяжи 2–4 конкретных ответа с именами, затем заверши своей репликой к ребятам. '
        'Цитируй только если это помогает истории; не повторяй перед каждым именем «пишет», «отмечает», «вспоминает». Не подсчитывай настроение и участников. '
        'Хвали только конкретный поступок из ответов. Остроумие по обстоятельствам, без обязательной шутки. Не высмеивай детей. '
        'Ты прочитал ответы, но не видел событий. Не придумывай обстоятельства, связи между людьми, привычки, причины настроения, диалоги и содержание фотографий. '
        'Не объявляй настроение всей группы одинаковым, если ответы разные. Имена сохраняй как в исходных данных. Не начинай с «В редакции», не используй метафоры про титры и общий эфир. '
        'Если есть game_participants, вплети в вечерний рассказ, кто сегодня со мной играл. Имена назови; спасибо всем за участие, все молодцы за то, что попробовали и разобрали решения. '
        'Не утверждай, что все ответили верно, если это не так. Мягко предложи потренировать конкретный навык из missed, без публичного разбора ошибок отдельного ребёнка. '
        +('Это утро. Последняя фраза: вернусь с лайфхаком в 15:00.' if morning else 'Это вечер. Заверши пожеланием хорошего вечера, а в пятницу — хороших выходных.')+
        ' Без заголовка, HTML, Markdown и эмодзи. Верни JSON {"text":"..."}.'
    )
    result=s['ai_json'](prompt,json.dumps({'date':s['today'](),'weekday':s['now']().weekday(),'answers':facts,'game_participants':games},ensure_ascii=False),750) if (facts or games) and s['AI_KEY'] else None
    candidate=str((result or {}).get('text','')).strip()
    if candidate:
        checked=s['ai_json']('Проверь рассказ по реальным ответам. Сохрани голос живого ведущего и связные полные предложения. Убери только придуманные факты о детях, событиях и фото; не превращай текст в список или обрывки. Не добавляй новых фактов. 450–850 знаков, 5–7 предложений. Верни JSON {"text":"..."}.',
                             json.dumps({'answers':facts,'game_participants':games,'draft':candidate},ensure_ascii=False),750)
        candidate=str((checked or {}).get('text','')).strip()
    sentences=len(re.findall(r'[.!?](?:\s|$)',candidate))
    bad=re.search(r'<[^>]+>|(?:^|\n)\s*(?:[•*]|\d+[.)])|не (?:смог|удалось).*?(?:обработ|разобра)|На связи \d',candidate,re.I)
    if not (350<=len(candidate)<=850 and sentences>=4 and not bad) or any(g['name'] not in candidate for g in games):candidate=fallback_story(rows,morning,games)
    if morning and '15:00' not in candidate:candidate+=' В 15:00 вернусь с лайфхаком.'
    with s['conn']() as c:
        c.execute('insert or ignore into daily_content(day,kind,title,body) values(?,?,?,?)',(s['today'](),kind,'Истории переклички',candidate))
    return candidate
