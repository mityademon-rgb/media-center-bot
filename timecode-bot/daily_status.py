"""Daily activity trophies; authoritative scores, persistent and retry-safe."""
import datetime as dt
import json
import urllib.parse
import editorial_voice

BADGES={'microphone':('🎙️','Золотой микрофон'),'camera':('🎥','Золотая видеокамера'),'lens':('📸','Шпионский объектив'),'leaf':('🌿','Лопушок на паузе')}

def install(s):
    original_init=s['init'];original_digest=s['digest'];original_story=editorial_voice.story
    original_out=s['Handler'].out
    def tables(c):
        c.execute('create table if not exists daily_status_rounds(day text primary key,announcement text not null)')
        c.execute('create table if not exists daily_status_users(user_id integer primary key,day text not null,badge text not null,actions integer not null)')
        c.execute('create table if not exists daily_status_history(day text not null,user_id integer not null,badge text not null,actions integer not null,primary key(day,user_id))')
    def init():
        original_init()
        with s['conn']() as c:tables(c)
    def current(uid):
        with s['conn']() as c:
            tables(c);r=c.execute('select * from daily_status_users where user_id=?',(uid,)).fetchone()
        if not r:return None
        icon,title=BADGES[r['badge']]
        return {'icon':icon,'title':title,'badge':r['badge'],'day':r['day'],'actions':r['actions']}
    def display(uid,name):
        badge=current(uid)
        return (badge['icon']+' ' if badge else '')+name
    def settle():
        day=s['today']()
        with s['conn']() as c:
            tables(c)
            old=c.execute('select announcement from daily_status_rounds where day=?',(day,)).fetchone()
            if old:return old['announcement']
            users=c.execute("select id,name from users where enabled=1 and role!='admin'").fetchall()
            records=[]
            for u in users:
                uid=u['id'];actions=0;photo=False;correct=False
                for table in ('morning_checkins','evening_checkins'):
                    r=c.execute('select mood,photo,step from '+table+' where user_id=? and day=?',(uid,day)).fetchone()
                    if r and r['step']=='done':
                        actions+=int(bool(r['mood']) and r['mood']!='Фотоохота');photo=photo or bool(r['photo'])
                if c.execute('select 1 from daily_photos where user_id=? and day=?',(uid,day)).fetchone():photo=True
                actions+=int(photo)
                played=False
                if c.execute("select 1 from sqlite_master where name='truth_results'").fetchone():
                    r=c.execute('select score from truth_results where day=? and user_id=?',(day,uid)).fetchone()
                    if r:played=True;correct=r['score']>0
                if c.execute("select 1 from sqlite_master where name='chat_game_runs'").fetchone():
                    rows=c.execute('select step,score from chat_game_runs where user_id=? and day=? and step>0',(uid,day.replace('-',''))).fetchall()
                    if rows:played=True;correct=correct or any(r['score']>0 for r in rows)
                actions+=int(played)
                records.append({'id':uid,'name':u['name'],'actions':actions,'photo':photo,'correct':correct})
            ranked=sorted((r for r in records if r['actions']>=2),key=lambda r:-r['actions'])
            cutoff=ranked[min(2,len(ranked)-1)]['actions'] if ranked else 99
            winners=ranked if users and len(ranked)==len(users) else [r for r in ranked if r['actions']>=cutoff]
            award_lines=[]
            for r in records:
                previous=c.execute('select badge from daily_status_users where user_id=?',(r['id'],)).fetchone()
                badge=('microphone' if r['correct'] else 'camera' if r['photo'] else 'lens') if r in winners else 'leaf' if r['actions']==0 and previous else None
                if badge is None:
                    # A little participation preserves yesterday's trophy; a silent day replaces it.
                    continue
                c.execute('insert into daily_status_users values(?,?,?,?) on conflict(user_id) do update set day=excluded.day,badge=excluded.badge,actions=excluded.actions',(r['id'],day,badge,r['actions']))
                c.execute('insert or ignore into daily_status_history values(?,?,?,?)',(day,r['id'],badge,r['actions']))
                icon,title=BADGES[badge]
                if badge!='leaf':award_lines.append(icon+' '+r['name']+' — '+title)
                if previous and previous['badge']!='leaf' and badge=='leaf':
                    text='Сегодня твой микрофон и камера отдыхают. Выдаю 🌿 «Лопушок на паузе». Вернёшься в игру — будет повод сменить аватар.'
                    c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(day,'status-pause:'+str(r['id']),json.dumps(r['id']),text,'null'))
            text=('Сегодня самые активные получают мои статусы:\n'+'\n'.join(award_lines)+'\nДо следующих итогов значок будет рядом с вашим именем. Завтра разыграем статусы снова.') if award_lines else 'Сегодня трофеи остались в кофре. Завтра снова разыграем их: выходи на связь и сыграй со мной.'
            c.execute('insert into daily_status_rounds values(?,?)',(day,text))
            return text
    def digest(period):
        if period=='pm':settle()
        return original_digest(period)
    def story(scope,rows,morning):
        named=[dict(r,name=display(r['user_id'],r['name'])) if 'user_id' in r.keys() else r for r in rows]
        result=original_story(scope,named,morning)
        if not morning:result+='\n\n'+settle()
        return result
    def out(handler,data,*args,**kwargs):
        if urllib.parse.urlsplit(handler.path).path=='/api/state' and isinstance(data,dict) and data.get('me'):
            data['me']['daily_status']=current(data['me']['id'])
        return original_out(handler,data,*args,**kwargs)
    editorial_voice.story=story
    s['Handler'].out=out
    s.update(init=init,digest=digest,evening_digest=lambda:digest('pm'),daily_status=current,status_settle=settle,display_name=display)
