"""Single-form schedule updates with authenticated teacher access and durable alerts."""
import datetime as dt
import re
import urllib.parse


def act(c, p, today):
    kind=p.get('kind');action=p.get('action')
    table={'lesson':'lessons','override':'overrides'}.get(kind)
    if not table or action not in ('save','remove'):raise ValueError('Неизвестное действие')
    row=None
    if p.get('id') is not None:
        row=c.execute('select * from '+table+' where id=?',(int(p['id']),)).fetchone()
        if not row or (kind=='lesson' and not row['enabled']):raise ValueError('Занятие уже удалено. Обнови расписание.')
        if p.get('original')!=dict(row):raise ValueError('Расписание уже изменилось. Обнови его перед сохранением.')
    if action=='remove':
        if not row:raise ValueError('Выбери занятие')
        if kind=='lesson':
            c.execute('update lessons set enabled=0 where id=?',(row['id'],))
            detail=row['start']+' · '+row['title']+' · удалено из постоянного расписания'
        else:
            c.execute('delete from overrides where id=?',(row['id'],))
            detail=row['day']+' · отдельное изменение убрано, действует обычное расписание'
        return row['lab'],detail
    lab=p.get('lab')
    if lab not in ('kids','media'):raise ValueError('Выбери лабораторию')
    title=str(p.get('title') or '').strip();place=str(p.get('place') or '').strip()
    cancelled=kind=='override' and p.get('cancelled') is True
    start=str(p.get('start') or '')
    if cancelled:start='00:00';title='Занятие отменено';place=''
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',start):raise ValueError('Укажи время: 18:00')
    if not 1<=len(title)<=90 or len(place)>80:raise ValueError('Тема — до 90 знаков, место — до 80')
    if kind=='lesson':
        weekday=int(p.get('weekday',-1))
        if not 0<=weekday<=6:raise ValueError('Выбери день недели')
        if row:c.execute('update lessons set lab=?,weekday=?,start=?,title=?,place=? where id=?',(lab,weekday,start,title,place,row['id']))
        else:c.execute('insert into lessons(lab,weekday,start,title,place) values(?,?,?,?,?)',(lab,weekday,start,title,place))
        detail=('Пн','Вт','Ср','Чт','Пт','Сб','Вс')[weekday]+' '+start+' · '+title+(' · '+place if place else '')
    else:
        day=dt.date.fromisoformat(str(p.get('day','')))
        if day<dt.date.fromisoformat(today):raise ValueError('Дата уже прошла')
        # A date replacement is intentionally one record per laboratory and date.
        if row:c.execute('delete from overrides where id=?',(row['id'],))
        c.execute('delete from overrides where lab=? and day=?',(lab,day.isoformat()))
        c.execute('insert into overrides(day,lab,start,title,place,cancelled) values(?,?,?,?,?,?)',(day.isoformat(),lab,start,title,place,int(cancelled)))
        detail=day.isoformat()+' · '+('занятие отменено' if cancelled else start+' · '+title+(' · '+place if place else ''))
    return lab,detail


def install(s):
    handler=s['Handler'];original=handler.do_POST
    def post(self):
        if urllib.parse.urlsplit(self.path).path!='/api/schedule-edit':return original(self)
        user=self.identity()
        if not user or user['role']!='admin':return self.out({'error':'Нет доступа'},403)
        try:
            p=self.body(12000)
            if not isinstance(p,dict):raise ValueError('Не удалось прочитать форму')
            with s['conn']() as c:
                lab,detail=act(c,p,s['today']())
                key=s['schedule_queue_change'](c,lab,detail)
        except (TypeError,ValueError,KeyError) as error:return self.out({'error':str(error) if isinstance(error,ValueError) else 'Проверь поля формы'},400)
        try:s['retry_notifications'](key)
        except Exception as error:print('Schedule alert queued:',type(error).__name__,flush=True)
        return self.out({'ok':True})
    handler.do_POST=post
