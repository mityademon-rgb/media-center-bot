"""One-tap characters and concrete photo hunts, shared by Telegram and MAX."""
import datetime as dt
import json
import shared_media

STATES={
 'am':(('🧟‍♂️ Я зомби, несу свой рюкзак','Рюкзак доставлен. Осталось доставить его владельца.'),
       ('⚡ Батарейка на 100%','Запомню тебя таким. После третьего урока сравним.'),
       ('🦥 Я ленивец, разбудите в субботу','План красивый. Но в субботу Дмитрий Витальевич ждёт на занятии — придётся пересмотреть.'),
       ('🥞 Сначала завтрак, потом разговоры','Принято. С блином за твоё внимание конкурировать бессмысленно.')),
 'pm':(('🍿 Режим зрителя','Плед занял режиссёрское кресло. Сегодня ему можно.'),
       ('🧠 Монтажный брак','Этот день больше не монтируем. Сохраняем проект и закрываем.'),
       ('🔋 1% и держусь на честном слове','Честное слово — достойный аккумулятор. Но розетка надёжнее.'),
       ('🚀 Готов снимать шедевры','У команды второе дыхание. Только проверь, осталось ли первое у камеры.'))}
HUNTS={
 'am':('Найди один ярко-красный предмет. Сними так, будто это важная улика.',
       'Покажи часы необычным ракурсом: снизу, сбоку или совсем близко. Лица людей в кадре не нужны.',
       'Найди предмет с «лицом»: розетку, застёжку или узор. Сфотографируй того, кто на тебя смотрит.',
       'Сними деталь очень близко, чтобы сразу не было понятно, что это. Вечером раскрывать тайну необязательно.',
       'Поймай смешную тень предмета. Сам предмет можно оставить за кадром.',
       'Найди предмет, который выглядит ещё более сонным, чем ты. Один кадр — и возвращайся к завтраку.',
       'Найди отражение в ложке, стекле или луже. Посмотрим, как мир там перекосило.'),
 'pm':('Сними самый уютный свет рядом: лампу, гирлянду или пятно света на стене.',
       'Найди предмет, который тоже выглядит уставшим. Посмотрим, кому сегодня досталось больше.',
       'Найди рядом что-нибудь круглое и сними крупно. Сегодня у нас охота на круги.',
       'Сними предмет с длинной тенью. Пусть обычная вещь сыграет в маленьком хорроре.',
       'Покажи одну деталь своего вечера: чашку, книгу, наушники. Приблизь камеру, убери лишнее.',
       'Найди два предмета одного цвета. Попробуй уместить их в одном кадре.',
       'Найди предмет с «лицом», которому пора спать. Сними его вечерний портрет.')}
SELFIES=(
 'Ты диктор новостей. В эфире срочная новость: школьная столовая объявила выходной. Сними селфи с лицом человека, который обязан сохранить серьёзность.',
 'Ты ведущий тревел-программы. Прилетел в город, где всё сделано из шоколада. Сними селфи: восторг уже есть, профессиональная выдержка ещё борется.',
 'Ты журналист в эпицентре событий: кот захватил твоё кресло. Сними лицо корреспондента, который ведёт репортаж с места этого переворота.',
 'Ты ведущий прогноза погоды. Обещал солнце, а за окном снег из попкорна. Сними селфи: как будешь держаться в эфире?',
 'Ты спортивный комментатор. Последняя секунда матча — и победный гол. Сними лицо в тот самый момент. Кричать на весь дом необязательно.',
 'Ты интервьюер. Гость только что заявил, что никогда не видел телефона. Сними свою реакцию: удивление есть, вежливость тоже должна остаться.',
 'Ты ведущий новостей. Суфлёр погас, но камера работает. Сними селфи человека, который делает вид, что всё было задумано именно так.')

def hunt(day,period):return HUNTS[period][dt.date.fromisoformat(day).toordinal()%len(HUNTS[period])]

def install(s):
    old_message=s['bot_message'];old_callback=s['callback'];old_init=s['init']
    def tables(c):
        c.execute('''create table if not exists photo_hunts(user_id integer not null,day text not null,period text not null,task text not null,comment text not null default '',primary key(user_id,day,period))''')
    def init():
        old_init()
        with s['conn']() as c:tables(c)

    def keys(period):
        return [[{'text':item[0],'callback_data':f'pc:{period}:{i}:{s["today"]()}'}] for i,item in enumerate(STATES[period])]

    def offer(uid,period):
        with s['conn']() as c:c.execute('update users set stage=? where id=?',('morning:photo' if period=='am' else 'evening:photo',uid))
        s['send'](uid,'📸 Фотоохота: '+hunt(s['today'](),period)+'\n\nПришли один кадр сюда, если хочется. Можно просто выбрать состояние и на этом закончить.',
                  [[{'text':'На сегодня без кадра','callback_data':f'pc:{period}:skip:{s["today"]()}'}]])

    def invitation(period):
        weekend=s['now']().weekday()>=5
        when='09:00' if weekend else '07:30'
        weekday=('понедельник','вторник','среда','четверг','пятница','суббота','воскресенье')[s['now']().weekday()]
        date=s['now']().strftime('%d.%m.%Y')+' · '+weekday
        text=('☀️ '+when+' / ДОБРОЕ УТРО'+(' ВЫХОДНОГО ДНЯ' if weekend else '')+'!\n'+date+'\n\nКто сегодня несёт тебя на первый урок? Выбирай свой режим. Одного нажатия достаточно.' if period=='am' else
              '🎬 ТИТРЫ И ЗАНАВЕС\n'+date+'\n\nСмена окончена. Какой у тебя финал?\n🍿 Плед, кино и чай\n🧠 Голова не варит, уроки добили\n🔋 Не трогать до утра\n🚀 Второе дыхание, полон сил')
        close=('09:50' if weekend else '09:00') if period=='am' else '20:00'
        text+='\n\n📸 Фотоохота: '+hunt(s['today'](),period)+'\nМожно прислать фото сразу — без анкеты и объяснений. Жду до '+close+'. В '+('10:00' if period=='am' else '20:30')+' соберу ваши режимы и кадры в общий рассказ.'
        with s['conn']() as c:targets=[r['id'] for r in c.execute('select id from users where enabled=1')]
        for uid in targets:s['send'](uid,text,keys(period))
        if s.get('GROUP'):s['send'](s['GROUP'],text+'\nВыбирай режим в личном чате с ботом.')

    def callback(q):
        data=q.get('data','');uid=(q.get('from') or {}).get('id')
        if data.startswith(('morning:','evening:')):
            period='am' if data.startswith('morning:') else 'pm'
            if q.get('id')!='max':s['api']('answerCallbackQuery',{'callback_query_id':q.get('id')})
            if s['allowed'](uid):s['send'](uid,'Теперь выбираем персонажа одним нажатием. Старую анкету убрали.',keys(period))
            return
        if not data.startswith('pc:'):return old_callback(q)
        if q.get('id')!='max':s['api']('answerCallbackQuery',{'callback_query_id':q.get('id')})
        if not s['allowed'](uid):return
        bits=data.split(':')
        if len(bits)!=4 or bits[1] not in STATES:return
        _,period,value,day=bits
        if day!=s['today']() or not s['checkin_open'](period):return s['send'](uid,'Этот выпуск уже собран. Новая охота будет в следующем приглашении.')
        if value=='skip':
            with s['conn']() as c:c.execute("update users set stage='' where id=? and stage in ('morning:photo','evening:photo')",(uid,))
            return s['send'](uid,'Договорились. Выбранный режим остаётся в нашем выпуске.')
        if not value.isdigit() or not 0<=int(value)<len(STATES[period]):return
        label,reaction=STATES[period][int(value)]
        table='morning_checkins' if period=='am' else 'evening_checkins'
        with s['conn']() as c:
            c.execute('insert into '+table+"(user_id,day,mood,step,visible) values(?,?,?,'done',1) on conflict(user_id,day) do update set mood=excluded.mood,step='done',visible=1",(uid,day,label))
        s['send'](uid,reaction)
        offer(uid,period)

    def message(msg):
        uid=(msg.get('from') or {}).get('id')
        if (msg.get('chat') or {}).get('type')!='private' or not uid or not s['allowed'](uid) or uid in s['ADMINS']:return old_message(msg)
        with s['conn']() as c:
            if c.execute("select 1 from sqlite_master where type='table' and name='notification_unreachable'").fetchone():
                c.execute('delete from notification_unreachable where chat=?',(json.dumps(uid),))
            row=c.execute('select stage from users where id=?',(uid,)).fetchone()
        stage=row['stage'] if row else ''
        photo=(msg.get('photo') or [{}])[-1].get('file_id','')
        if stage=='instant' and photo:
            s['accept_daily_photo'](uid,msg)
            url=str((msg.get('max_photo') or {}).get('url') or '')
            try:comment=s['photo_comment'](photo,url)
            except Exception:comment=''
            if comment:
                with s['conn']() as c:c.execute('update daily_photos set comment=? where user_id=? and day=? and photo=?',(comment[:700],uid,s['today'](),photo))
                s['send'](uid,s['esc'](comment[:700]))
            return
        period='am' if stage=='morning:photo' else 'pm' if stage=='evening:photo' else None
        if not period and photo and not stage:
            period='am' if s['checkin_open']('am') else 'pm' if s['checkin_open']('pm') else None
        if not period:return old_message(msg)
        if not photo:
            # A conversation stays a conversation; never demand a photograph in reply.
            if stage in ('morning:photo','evening:photo'):
                with s['conn']() as c:c.execute("update users set stage='' where id=?",(uid,))
            return old_message(msg)
        if not s['checkin_open'](period):
            with s['conn']() as c:c.execute("update users set stage='' where id=?",(uid,))
            return s['send'](uid,'Этот выпуск уже собран. Кадр можно приберечь для следующей охоты.')
        url=str((msg.get('max_photo') or {}).get('url') or '')
        shared_media.remember(s,photo,url)
        photo_task=hunt(s['today'](),period)
        table='morning_checkins' if period=='am' else 'evening_checkins'
        with s['conn']() as c:
            tables(c)
            c.execute('insert into '+table+"(user_id,day,mood,photo,step,visible) values(?,?,'Фотоохота',?,'done',1) on conflict(user_id,day) do update set photo=excluded.photo,step='done',visible=1",(uid,s['today'](),photo))
            c.execute('insert into photo_hunts(user_id,day,period,task) values(?,?,?,?) on conflict(user_id,day,period) do update set task=excluded.task,comment=\'\'',(uid,s['today'](),period,photo_task))
            caption=str(msg.get('caption') or '').strip()
            if caption:c.execute('update '+table+' set '+('important' if period=='am' else 'highlight')+'=? where user_id=? and day=?',(caption[:300],uid,s['today']()))
            c.execute("update users set stage='' where id=?",(uid,))
        s['send'](uid,'Кадр пойман. Прикреплю его с твоим именем к общему выпуску в '+('10:00' if period=='am' else '20:30')+'.')
        try:comment=s['photo_comment'](photo,url)
        except Exception:comment=''
        if comment:
            with s['conn']() as c:c.execute('update photo_hunts set comment=? where user_id=? and day=? and period=?',(comment[:700],uid,s['today'](),period))
            s['send'](uid,s['esc'](comment[:700]))

    def selfie():
        task=SELFIES[dt.date.fromisoformat(s['today']()).toordinal()%len(SELFIES)]
        text='🎭 16:00 / ТЫ В КАДРЕ\n\n'+task+'\n\nПришли одно фото сюда. Помни: я покажу тебя всем — прикреплю кадр с твоим именем к вечернему выпуску в Telegram и MAX. Участвовать можно по желанию.'
        with s['conn']() as c:rows=c.execute("select id from users where enabled=1 and role!='admin'").fetchall()
        for row in rows:
            with s['conn']() as c:c.execute("update users set stage='instant' where id=? and stage=''",(row['id'],))
            s['send'](row['id'],text)

    s.update(init=init,bot_message=message,callback=callback,morning=lambda:invitation('am'),evening=lambda:invitation('pm'),offer_checkin_photo=offer,reminder=lambda period:None,instant_photo=selfie)
