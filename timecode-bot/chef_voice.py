"""Persistent Kimi persona and a real, opt-in evening pilot."""
import json
from pathlib import Path
import playful_checkins

PILOT='Достань самую дешёвую вещь из рюкзака. Сними её как рекламу за миллион: свет от окна, чистый фон, предмет — звезда кадра.'

def install(s):
    memory=(Path(__file__).parent/'CHEF_MEMORY.md').read_text()
    original_request=s['kimi_request'];original_hunt=playful_checkins.hunt;old_callback=s['callback']
    def request(path,data,*args,**kwargs):
        if path=='/chat/completions' and isinstance(data,dict):
            data=dict(data);messages=[dict(m) for m in data.get('messages',[])]
            system=' '.join(str(m.get('content','')) for m in messages if m.get('role')=='system').lower()
            if not any(word in system for word in ('фактчекер','проверь','проверка','поисковую фразу','проверь по source')):
                instructions=memory+'\nСоблюдай формат JSON и ограничения конкретного запроса. Проверенные факты и реальная оценка важнее шутки.'
                if any(isinstance(m.get('content'),list) for m in messages):
                    with s['conn']() as c:r=c.execute("select body from daily_content where day=? and kind='chef-hunt-pm'",(s['today'](),)).fetchone()
                    if r:instructions+='\nСегодняшний фото-вызов: '+r['body']
                messages.append({'role':'system','content':instructions})
                data['messages']=messages
        return original_request(path,data,*args,**kwargs)
    def hunt(day,period):
        kind='chef-hunt-'+period
        with s['conn']() as c:r=c.execute('select body from daily_content where day=? and kind=?',(day,kind)).fetchone()
        if r:return r['body']
        result=s['ai_json']('Придумай фотоохоту Кими: один предмет, один приём, 60 секунд съёмки, понятный вызов подростку. До 220 знаков, 2–3 предложения. Используй банк направлений из памяти, вариации, не повторяй вчерашнее задание. Не обещай призы. JSON {"text":"..."}.',json.dumps({'day':day,'period':period}),250) if s.get('AI_KEY') else None
        text=str((result or {}).get('text','')).strip()
        if not 30<=len(text)<=240:text=original_hunt(day,period)
        with s['conn']() as c:
            c.execute('insert or ignore into daily_content(day,kind,title,body) values(?,?,?,?)',(day,kind,'Фотоохота Кими',text))
            return c.execute('select body from daily_content where day=? and kind=?',(day,kind)).fetchone()['body']
    def callback(q):
        data=q.get('data','')
        if not data.startswith('chef:'):return old_callback(q)
        uid=(q.get('from') or {}).get('id')
        if q.get('id')!='max':s['api']('answerCallbackQuery',{'callback_query_id':q.get('id')})
        if not s['allowed'](uid):return
        if data!='chef:pm:'+s['today']() or not s['checkin_open']('pm'):return s['send'](uid,'Смена свернулась, режиссёр ушёл пить лимонад. Жди следующего дубля!')
        with s['conn']() as c:c.execute("update users set stage='evening:photo' where id=?",(uid,))
        s['send'](uid,hunt(s['today'](),'pm')+' Пришли кадр до 20:00 — покажу всем в вечернем таблоиде.')
    def launch():
        day=s['today']()
        if day!='2026-10-09' or not s['checkin_open']('pm'):raise RuntimeError('Pilot must launch inside Friday evening window')
        body='🎬 ВБРОС ОТ КИМИ\n\nМассовка, проверим ваши амбиции. '+PILOT+'\n\nСъёмка на минуту. Нажми «Принять вызов» и присылай кадр до 20:00. В 20:30 покажу ваши попытки всем в таблоиде. Посмотрим, кому уже тесно в массовке.'
        keys=[[{'text':'🎬 Принять вызов','callback_data':'chef:pm:'+day}]]
        with s['conn']() as c:
            c.execute("insert into daily_content(day,kind,title,body) values(?,'chef-hunt-pm','Реклама за миллион',?) on conflict(day,kind) do update set body=excluded.body",(day,PILOT))
            targets=[r['id'] for r in c.execute('select id from users where enabled=1')]
            if s.get('GROUP'):targets.append(s['GROUP'])
            for chat in set(targets):c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(day,'chef-pilot-20261009',json.dumps(chat),body,json.dumps(keys,ensure_ascii=False)))
        s['retry_notifications']('chef-pilot-20261009')
    playful_checkins.hunt=hunt
    s.update(kimi_request=request,callback=callback,chef_launch=launch,chef_memory=memory)
