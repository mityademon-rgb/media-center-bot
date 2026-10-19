"""Teacher onboarding and a reversible subscription to TIMECODE daily life."""
import json
import threading
import urllib.parse
import shared_media

_scheduled = threading.local()


def install(ns):
    with ns['conn']() as c:
        c.execute('create table if not exists teacher_modes(user_id integer primary key, daily_enabled integer not null default 0)')

    def teacher(uid):
        with ns['conn']() as c:
            return c.execute("select role from users where id=?", (uid,)).fetchone()

    def daily_enabled(uid):
        with ns['conn']() as c:
            row = c.execute("select u.role, m.daily_enabled from users u left join teacher_modes m on m.user_id=u.id where u.id=?", (uid,)).fetchone()
        return bool(row and (row['role'] != 'teacher' or row['daily_enabled']))

    def paused_teacher(uid):
        row=teacher(uid)
        return bool(row and row['role']=='teacher' and not daily_enabled(uid))

    def pause_queued(c, uid):
        chat = json.dumps(uid)
        for table in ('notification_outbox', 'notification_photo_outbox'):
            c.execute('update ' + table + ' set delivered=-2 where chat=? and delivered=0', (chat,))

    def set_mode(uid, enabled):
        with ns['conn']() as c:
            c.execute('insert into teacher_modes(user_id,daily_enabled) values(?,?) on conflict(user_id) do update set daily_enabled=excluded.daily_enabled', (uid, int(enabled)))
            if not enabled:
                pause_queued(c, uid)
                c.execute("update users set stage='' where id=? and (stage like 'morning:%' or stage like 'evening:%' or stage like 'weekly:%' or stage in ('instant','mission'))", (uid,))

    def mode_buttons(uid):
        buttons = [[{'text': '🎓 Уроки по нейросетям', 'web_app': {'url': ns['BASE']}}]] if ns.get('BASE') else []
        buttons.append([{'text': '🔕 Отключить ежедневную жизнь' if daily_enabled(uid) else '🔔 Участвовать в ежедневной жизни',
                         'callback_data': 'teacher:daily:off' if daily_enabled(uid) else 'teacher:daily:on'}])
        return buttons

    def greeting(uid):
        active = daily_enabled(uid)
        ns['send'](uid, '<b>Привет! Вы в TIMECODE как преподаватель.</b>\n'
            'В приложении доступны уроки по нейросетям и помощник Кими. '
            + ('Вы также можете читать выпуски, играть и участвовать в заданиях и перекличках. '
               'Ежедневную жизнь можно выключить в любой момент: /daily off или кнопкой ниже.'
               if active else
               'Сейчас ежедневные задания, переклички и выпуски в личный бот выключены. '
               'Чтобы участвовать, отправьте /daily on или нажмите кнопку ниже.'),
            mode_buttons(uid))

    def attendance(uid):
        ns['send'](uid, '<b>Ты занимаешься в TIMECODE?</b>\n'
            'Если да — выбери «Да», и мы откроем обычную жизнь медиацентра. '
            'Если нет и ты преподаватель — выбери «Нет»: покажу уроки по нейросетям '
            'и спрошу, хочешь ли ты участвовать в ежедневной жизни бота.',
            [[{'text':'Да, занимаюсь','callback_data':'onboard:attendance:yes'},
              {'text':'Нет, я преподаватель','callback_data':'onboard:attendance:no'}]])

    def participation(uid):
        ns['send'](uid, '<b>Привет! Рад видеть вас в TIMECODE.</b>\n'
            'Здесь, как и у ребят, есть игры, приёмы дня, задания и утренняя и вечерняя переклички. '
            'Если хотите участвовать в ежедневной жизни бота, ответьте «Да». '
            'Если нет — открою только уроки по нейросетям и помощника Кими. '
            'Позже выбор можно изменить кнопкой в приложении или командой /daily on либо /daily off.',
            [[{'text':'Да, хочу участвовать','callback_data':'onboard:daily:yes'},
              {'text':'Нет, только уроки','callback_data':'onboard:daily:no'}]])

    def choose(uid, choice):
        with ns['conn']() as c:
            row = c.execute('select stage from users where id=?', (uid,)).fetchone()
        stage = row['stage'] if row else ''
        if stage == 'onboard:attendance' and choice in ('yes','no'):
            if choice == 'no':
                with ns['conn']() as c:
                    c.execute("update users set role='teacher',stage='onboard:teacher_daily' where id=?", (uid,))
                    c.execute('insert or ignore into teacher_modes(user_id,daily_enabled) values(?,0)', (uid,))
                participation(uid)
            else:
                with ns['conn']() as c:c.execute("update users set stage='onboard:lab' where id=?", (uid,))
                ns['send'](uid, '🎬 Отлично! Выбери свою лабораторию.',
                    [[{'text':'Я в Kids Lab','callback_data':'onboard:lab:kids'},
                      {'text':'Я в Media Lab','callback_data':'onboard:lab:media'}]])
            return True
        if stage == 'onboard:teacher_daily' and choice in ('yes','no'):
            with ns['conn']() as c:c.execute("update users set stage='' where id=?", (uid,))
            set_mode(uid, choice == 'yes')
            greeting(uid)
            return True
        if stage == 'onboard:lab' and choice in ('kids','media'):
            with ns['conn']() as c:c.execute("update users set lab=?,stage='' where id=?", (choice,uid))
            ns['send'](uid, '🎬 Теперь ты в '+('Kids Lab' if choice=='kids' else 'Media Lab')+'. Игры, расписание и уроки ждут в приложении.',
                [[{'text':'Открыть TIMECODE ↗','web_app':{'url':ns['BASE']}}]] if ns.get('BASE') else None)
            return True
        return False

    old_roster = ns['roster']
    def roster(uid, name):
        with ns['conn']() as c:exists = c.execute('select 1 from users where id=?', (uid,)).fetchone()
        old_roster(uid, name)
        if not exists and uid not in ns['ADMINS']:
            with ns['conn']() as c:c.execute("update users set stage='onboard:attendance' where id=?", (uid,))
    ns['roster'] = roster

    old_message = ns['bot_message']
    def bot_message(msg):
        chat=msg.get('chat') or {}
        uid=(msg.get('from') or {}).get('id')
        if chat.get('type')!='private' or not uid:return old_message(msg)
        text=(msg.get('text') or '').strip()
        if not ns['allowed'](uid):
            roster(uid, ' '.join(filter(None,((msg.get('from') or {}).get('first_name',''), (msg.get('from') or {}).get('last_name','')))) or 'Участник')
        with ns['conn']() as c:
            row=c.execute('select stage,role from users where id=?',(uid,)).fetchone()
        if not row:return old_message(msg)
        if row['stage']=='onboard:attendance':
            if text.lower() in ('да','нет') and not text.startswith('/'):
                choose(uid, 'yes' if text.lower()=='да' else 'no')
            else:attendance(uid)
            return
        if row['stage']=='onboard:teacher_daily':
            if text.lower() in ('да','нет') and not text.startswith('/'):
                choose(uid, 'yes' if text.lower()=='да' else 'no')
            else:participation(uid)
            return
        if row['stage']=='onboard:lab':
            ns['send'](uid,'Выбери лабораторию кнопкой: Kids Lab или Media Lab.',
                [[{'text':'Kids Lab','callback_data':'onboard:lab:kids'},
                  {'text':'Media Lab','callback_data':'onboard:lab:media'}]])
            return
        if row['role']=='teacher':
            if text in ('/daily','/mode'):
                greeting(uid);return
            if text in ('/daily on','/daily off'):
                set_mode(uid,text.endswith('on'));greeting(uid);return
            if text.startswith('/start'):
                greeting(uid);return
        return old_message(msg)
    ns['bot_message']=bot_message

    old_callback=ns['callback']
    def callback(q):
        uid=(q.get('from') or {}).get('id');data=q.get('data','')
        if uid and (data.startswith('onboard:attendance:') or data.startswith('onboard:daily:') or data.startswith('onboard:lab:') or data.startswith('teacher:daily:')):
            if data.startswith('onboard:lab:') and not choose(uid,data.rsplit(':',1)[-1]):
                return old_callback(q)
            if q.get('id')!='max':ns['api']('answerCallbackQuery',{'callback_query_id':q.get('id')})
            if data.startswith('onboard:attendance:'):
                choose(uid,data.rsplit(':',1)[-1])
            elif data.startswith('onboard:daily:'):
                choose(uid,data.rsplit(':',1)[-1])
            elif data.startswith('teacher:daily:') and (r:=teacher(uid)) and r['role']=='teacher':
                set_mode(uid,data.endswith(':on'));greeting(uid)
            return
        return old_callback(q)
    ns['callback']=callback

    old_scheduler=ns['scheduler']
    def scheduler():
        _scheduled.active=True
        try:return old_scheduler()
        finally:_scheduled.active=False
    ns['scheduler']=scheduler
    old_send=ns['send']
    def send(chat, body, keyboard=None):
        if isinstance(chat,int) and paused_teacher(chat):
            if getattr(_scheduled,'active',False):return {'ok':True,'suppressed':True}
            with ns['conn']() as c:
                queued=c.execute('select 1 from notification_outbox where chat=? and body=? and delivered=0 limit 1',(json.dumps(chat),body)).fetchone()
            if queued:return {'ok':True,'suppressed':True}
        return old_send(chat,body,keyboard)
    ns['send']=send
    old_send_photo=shared_media.send_photo
    def send_photo(context, chat, photo, caption):
        if isinstance(chat,int) and paused_teacher(chat):
            return {'ok':True,'suppressed':True}
        return old_send_photo(context,chat,photo,caption)
    shared_media.send_photo=send_photo
    old_api=ns['api']
    def api(method,data=None):
        chat=(data or {}).get('chat_id')
        if getattr(_scheduled,'active',False) and method in ('sendMessage','sendPhoto','sendMediaGroup') and isinstance(chat,int) and paused_teacher(chat):
            return {'ok':True,'suppressed':True}
        return old_api(method,data)
    ns['api']=api
    old_retry=ns['retry_notifications']
    def retry_notifications(*args,**kwargs):
        with ns['conn']() as c:
            for row in c.execute("select id from users where role='teacher'").fetchall():
                if not daily_enabled(row['id']):pause_queued(c,row['id'])
        return old_retry(*args,**kwargs)
    ns['retry_notifications']=retry_notifications

    handler=ns['Handler']
    old_out,old_post=handler.out,handler.do_POST
    def out(self, data, status=200):
        if urllib.parse.urlsplit(self.path).path=='/api/state' and status==200 and isinstance(data,dict) and isinstance(data.get('me'),dict):
            me=data['me'];me['daily_enabled']=daily_enabled(me['id'])
            if me['role']=='teacher' and not me['daily_enabled']:
                data.update(quests=[],lessons=[],changes=[],latest=[],tip=None,mission=None)
        return old_out(self,data,status)
    def post(self):
        path=urllib.parse.urlsplit(self.path).path
        if path=='/api/teacher-mode':
            user=self.identity()
            if not user:return self.out({'error':'Сначала войдите'},401)
            if user['role']!='teacher':return self.out({'error':'Только для преподавателя'},403)
            data=self.body()
            if not isinstance(data,dict) or type(data.get('enabled')) is not bool:return self.out({'error':'Выберите режим'},400)
            set_mode(user['id'],data['enabled'])
            return self.out({'ok':True,'daily_enabled':data['enabled']})
        if path.startswith('/api/') and path not in ('/api/auth','/api/max/webhook','/api/neuro'):
            user=self.identity()
            if user and user['role']=='teacher' and not daily_enabled(user['id']):
                return self.out({'error':'Сейчас доступны только уроки по нейросетям. Включите участие в профиле.'},403)
        return old_post(self)
    handler.out,handler.do_POST=out,post
    ns['teacher_daily_enabled']=daily_enabled
