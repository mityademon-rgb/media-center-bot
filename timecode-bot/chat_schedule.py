"""Teacher schedule editing through chat buttons, shared by Telegram and MAX."""
import datetime as dt
import hashlib
import json
import time

WEEK=('Пн','Вт','Ср','Чт','Пт','Сб','Вс')


def install(s):
    original_message=s['bot_message'];original_callback=s['callback']

    def table(c):
        c.execute('create table if not exists admin_schedule_drafts(user_id integer primary key,body text not null)')

    def save(uid,draft):
        with s['conn']() as c:
            table(c)
            c.execute('insert or replace into admin_schedule_drafts values(?,?)',(uid,json.dumps(draft,ensure_ascii=False)))

    def read(uid):
        with s['conn']() as c:
            table(c);r=c.execute('select body from admin_schedule_drafts where user_id=?',(uid,)).fetchone()
        return json.loads(r['body']) if r else None

    def clear(uid):
        with s['conn']() as c:table(c);c.execute('delete from admin_schedule_drafts where user_id=?',(uid,))

    def say(uid,text,keyboard=None):return s['send'](uid,text,keyboard)

    def queue_change(c,lab,detail):
        label='Kids Lab' if lab=='kids' else 'Media Lab'
        body='<b>Расписание изменилось!</b>\n'+label+' · '+s['esc'](detail)+'\n\n<b>Загляни в расписание!!!</b>'
        keyboard=[[{'text':'Открыть расписание','web_app':{'url':s['BASE']+'/?view=schedule'}}]] if s.get('BASE') else None
        key=hashlib.sha256((body+str(time.time_ns())).encode()).hexdigest()[:24]
        targets=[r['id'] for r in c.execute('select id from users where enabled=1')]
        if s.get('GROUP'):targets.append(s['GROUP'])
        for target in set(targets):
            c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',
                      (s['today'](),key,json.dumps(target),body,json.dumps(keyboard,ensure_ascii=False)))
        return key

    def changed(lab,detail):
        with s['conn']() as c:key=queue_change(c,lab,detail)
        s['retry_notifications'](key)

    def menu(uid):
        if uid not in s['ADMINS']:return
        clear(uid)
        with s['conn']() as c:
            c.execute("update users set stage='' where id=?",(uid,))
            rows=c.execute('select * from lessons where enabled=1 order by lab,weekday,start').fetchall()
        lines=['<b>Расписание занятий</b>']
        for lab,label in (('kids','Kids Lab'),('media','Media Lab')):
            lines.append('\n<b>'+label+'</b>')
            current=[r for r in rows if r['lab']==lab]
            lines.extend(WEEK[r['weekday']]+' '+r['start']+' · '+s['esc'](r['title'])+' · '+s['esc'](r['place']) for r in current)
            if not current:lines.append('Постоянных занятий пока нет.')
        say(uid,'\n'.join(lines)+'\n\nЧто меняем?',[
            *([[{'text':'Открыть удобный редактор','web_app':{'url':s['BASE']+'/?view=schedule'}}]] if s.get('BASE') else []),
            [{'text':'Изменить занятие в неделе','callback_data':'sch:action:edit'}],
            [{'text':'Добавить в неделю','callback_data':'sch:action:add'}],
            [{'text':'Удалить занятие из недели','callback_data':'sch:action:delete'}],
            [{'text':'Изменение на одну дату','callback_data':'sch:action:change'}],
            [{'text':'Отмена на одну дату','callback_data':'sch:action:cancel'}]])

    def ask(uid,d):
        prompts={'date':'Напиши дату занятия: например, 2026-10-05 или 05.10.2026.',
                 'time':'Во сколько начнётся занятие? Напиши время, например 18:00.',
                 'title':'Напиши тему или название занятия.',
                 'place':'Где будет занятие? Напиши кабинет или место. Если место не нужно, отправь —.'}
        say(uid,prompts[d['step']]+'\n/stop — отменить изменение.')

    def preview(uid,d):
        when=d.get('day') or WEEK[d['weekday']]
        label='Kids Lab' if d['lab']=='kids' else 'Media Lab'
        text='<b>Проверь перед сохранением</b>\n'+label+' · '+when
        if d['action']=='delete':text+=' · '+d['time']+'\n'+s['esc'](d['title'])+'\nУдалить это постоянное занятие из расписания? Отдельные изменения на даты сохранятся.'
        elif d['action']=='cancel':text+='\nЗанятие отменяется только на эту дату.'
        else:text+=' · '+d['time']+'\n'+s['esc'](d['title'])+'\n'+s['esc'](d['place'])
        d['step']='confirm';save(uid,d)
        say(uid,text,[[{'text':'Удалить' if d['action']=='delete' else 'Сохранить','callback_data':'sch:commit'}, {'text':'Отмена','callback_data':'sch:back'}]])

    def commit(uid):
        d=read(uid)
        if not d or d.get('step')!='confirm':return menu(uid)
        with s['conn']() as c:
            # Claim this draft once, so a repeated Save cannot add a second lesson.
            row=c.execute('select body from admin_schedule_drafts where user_id=?',(uid,)).fetchone()
            if not row or json.loads(row['body']).get('step')!='confirm':return
            c.execute('delete from admin_schedule_drafts where user_id=?',(uid,))
            if d['action']=='delete':
                removed=c.execute('update lessons set enabled=0 where id=? and lab=? and enabled=1',(d['lesson_id'],d['lab'])).rowcount
                if not removed:raise ValueError('Занятие уже удалено. Открой расписание снова.')
            elif d['action']=='edit':
                changed=c.execute('update lessons set weekday=?,start=?,title=?,place=? where id=? and lab=? and enabled=1',
                                  (d['weekday'],d['time'],d['title'],d['place'],d['lesson_id'],d['lab'])).rowcount
                if not changed:raise ValueError('Занятие уже изменилось. Открой расписание снова.')
            elif d['action']=='add':
                c.execute('insert into lessons(lab,weekday,start,title,place) values(?,?,?,?,?)',(d['lab'],d['weekday'],d['time'],d['title'],d['place']))
            else:
                c.execute('delete from overrides where lab=? and day=?',(d['lab'],d['day']))
                c.execute('insert into overrides(day,lab,start,title,place,cancelled) values(?,?,?,?,?,?)',
                          (d['day'],d['lab'],d.get('time','00:00'),d.get('title','Занятие отменено'),d.get('place',''),int(d['action']=='cancel')))
            when=d.get('day') or WEEK[d['weekday']]
            detail=when+' · '+('занятие отменено' if d['action']=='cancel' else d['time']+' · '+d['title']+(' · '+d['place'] if d['place'] else ''))
            if d['action']=='delete':detail+=' · удалено из постоянного расписания'
            key=queue_change(c,d['lab'],detail)
        s['retry_notifications'](key)
        say(uid,'Сохранил. Расписание в приложении обновлено, сообщение об изменении отправлено в очередь рассылки всем подписчикам Telegram и MAX.',
            [[{'text':'К расписанию','callback_data':'admin:schedule'}]])

    def callback(q):
        data=q.get('data','')
        if data!='admin:schedule' and not data.startswith('sch:'):return original_callback(q)
        uid=q.get('from',{}).get('id')
        if uid not in s['ADMINS']:return
        if q.get('id')!='max':s['api']('answerCallbackQuery',{'callback_query_id':q['id']})
        try:
            if data in ('admin:schedule','sch:back'):return menu(uid)
            if data=='sch:commit':return commit(uid)
            bits=data.split(':');kind=bits[1];value=bits[2]
            if kind=='action' and value in ('edit','add','change','cancel','delete'):
                save(uid,{'action':value,'step':'lab'})
                return say(uid,'Для какой группы?',[[{'text':'Kids Lab','callback_data':'sch:lab:kids'},{'text':'Media Lab','callback_data':'sch:lab:media'}]])
            d=read(uid)
            if not d:return menu(uid)
            if kind=='lab' and d['step']=='lab' and value in ('kids','media'):
                d['lab']=value
                if d['action'] in ('edit','delete'):
                    with s['conn']() as c:rows=c.execute('select * from lessons where lab=? and enabled=1 order by weekday,start',(value,)).fetchall()
                    if not rows:return say(uid,'У этой группы пока нет занятий. Выбери «Добавить в неделю».',[[{'text':'К расписанию','callback_data':'sch:back'}]])
                    d['step']='lesson';save(uid,d)
                    return say(uid,'Какое занятие изменить?',[[{'text':WEEK[r['weekday']]+' '+r['start']+' · '+r['title'][:35],'callback_data':'sch:lesson:'+str(r['id'])}] for r in rows])
                if d['action']=='add':
                    d['step']='weekday';save(uid,d)
                    return say(uid,'В какой день недели?',[[{'text':label,'callback_data':'sch:weekday:'+str(index)}] for index,label in enumerate(WEEK)])
                d['step']='date';save(uid,d);return ask(uid,d)
            if kind=='lesson' and d['step']=='lesson':
                with s['conn']() as c:r=c.execute('select * from lessons where id=? and lab=? and enabled=1',(int(value),d['lab'])).fetchone()
                if not r:raise ValueError('Занятие не найдено. Открой расписание снова.')
                if d['action']=='delete':
                    d.update(lesson_id=r['id'],weekday=r['weekday'],time=r['start'],title=r['title'],place=r['place'])
                    return preview(uid,d)
                d.update(lesson_id=r['id'],weekday=r['weekday'],step='weekday')
                save(uid,d)
                return say(uid,'Выбери день недели. Можно оставить прежний: '+WEEK[r['weekday']]+'.',[[{'text':label,'callback_data':'sch:weekday:'+str(index)}] for index,label in enumerate(WEEK)])
            if kind=='weekday' and d['step']=='weekday' and value.isdigit() and 0<=int(value)<=6:
                d.update(weekday=int(value),step='time');save(uid,d);return ask(uid,d)
            say(uid,'Эта кнопка уже устарела. Открой «📅 Расписание» заново.')
        except (ValueError,IndexError,KeyError) as error:say(uid,str(error) if isinstance(error,ValueError) else 'Не получилось прочитать действие. Открой расписание заново.')

    def message(msg):
        uid=msg.get('from',{}).get('id');text=msg.get('text','').strip()
        if uid not in s['ADMINS']:return original_message(msg)
        if text in ('📅 Расписание','/schedule'):return menu(uid)
        if text.startswith('/') or text in ('📣 Написать всем','👥 Подписчики','🎛 Управление','❓ Вопросы'):
            clear(uid);return original_message(msg)
        d=read(uid)
        if not d or d['step'] not in ('date','time','title','place'):return original_message(msg)
        try:
            step=d['step']
            if step=='date':
                date=dt.datetime.strptime(text,'%d.%m.%Y').date() if '.' in text else dt.date.fromisoformat(text)
                if date<s['now']().date():raise ValueError('Дата уже прошла. Укажи сегодняшнюю или будущую дату.')
                d['day']=date.isoformat()
                if d['action']=='cancel':return preview(uid,d)
                d['step']='time'
            elif step=='time':
                value=dt.time.fromisoformat(text)
                if value.second or value.tzinfo:raise ValueError('Нужно только время в формате 18:00.')
                d['time']=value.strftime('%H:%M');d['step']='title'
            elif step=='title':
                if not 1<=len(text)<=120:raise ValueError('Напиши название длиной до 120 знаков.')
                d['title']=text;d['step']='place'
            else:
                if len(text)>100:raise ValueError('Место — до 100 знаков.')
                d['place']='' if text in ('—','-') else text
                return preview(uid,d)
            save(uid,d);ask(uid,d)
        except ValueError:say(uid,'Не удалось прочитать значение. '+{'date':'Укажи дату: 2026-10-05 или 05.10.2026.','time':'Укажи время: 18:00.','title':'Напиши название до 120 знаков.','place':'Напиши место до 100 знаков.'}[d['step']])

    s.update({'bot_message':message,'callback':callback,'admin_schedule_menu':menu,'schedule_changed':changed,'schedule_queue_change':queue_change})
