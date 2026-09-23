import hashlib, hmac, html, json, mimetypes, os, re, secrets, sqlite3, threading, time, urllib.parse, urllib.request
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).parent; DB=Path(os.getenv('DATA_DIR',ROOT/'data'))/'group.db'; UP=Path(os.getenv('UPLOAD_DIR',ROOT/'uploads')); UP.mkdir(parents=True,exist_ok=True); DB.parent.mkdir(parents=True,exist_ok=True)
TOKEN=os.getenv('BOT_TOKEN',''); JOIN_CODE=os.getenv('JOIN_CODE',''); ADMIN_IDS={int(x) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip().isdigit()}; BASE=os.getenv('PUBLIC_URL','').rstrip('/'); GROUP=os.getenv('GROUP_NAME','КИНО / ГРУППА'); PORT=int(os.getenv('PORT','8080')); MAX_FILE=20*1024*1024

def conn():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row; c.execute('pragma journal_mode=WAL'); return c
with conn() as c:
 c.executescript('''create table if not exists users(id integer primary key, name text not null, username text, phone text default '', show_phone integer default 0, role text default 'student', joined integer not null, subscribed integer default 1); create table if not exists sessions(token text primary key,user_id integer not null,expires integer not null); create table if not exists codes(code text primary key,user_id integer not null,expires integer not null); create table if not exists posts(id integer primary key, kind text not null, title text not null, body text default '', file_id integer, pinned integer default 0, expires text default '', created integer not null, author integer); create table if not exists files(id integer primary key, storage text not null,name text not null,mime text not null,size integer not null); create table if not exists lessons(id integer primary key, weekday integer not null, start text not null, finish text not null, subject text not null, teacher text default '', room text default '', subgroup text default ''); create table if not exists changes(id integer primary key,day text not null,lesson_id integer,subject text not null,start text default '',finish text default '',teacher text default '',room text default '',note text default '',cancelled integer default 0,created integer not null); create table if not exists teachers(id integer primary key,name text not null, subject text default '', contact text default ''); create table if not exists resources(id integer primary key,title text not null,url text not null); create table if not exists deliveries(post_id integer,user_id integer, status text, primary key(post_id,user_id));''')

def api(method,payload):
 if not TOKEN: return {'ok':False,'description':'BOT_TOKEN не задан'}
 try:
  req=urllib.request.Request('https://api.telegram.org/bot'+TOKEN+'/'+method,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=25) as res:return json.load(res)
 except Exception as e:return {'ok':False,'description':str(e)}

def send(chat,text,markup=None):
 p={'chat_id':chat,'text':text,'parse_mode':'HTML'}
 if markup:p['reply_markup']=markup
 return api('sendMessage',p)

def notify(post_id):
 with conn() as c:
  p=c.execute('select p.*, f.name filename, f.storage from posts p left join files f on p.file_id=f.id where p.id=?',(post_id,)).fetchone()
  if not p:return
  users=c.execute('select id from users where subscribed=1').fetchall()
 for u in users:
  uid=u['id']; label={'announcement':'Объявление','deadline':'Дедлайн','change':'Замена'}.get(p['kind'],'Сообщение')
  body=f'<b>{html.escape(label)} · {html.escape(p["title"])}</b>\n{html.escape(p["body"] or "")}'
  result=send(uid,body)
  if result.get('ok') and p['storage']:
   try:
    boundary='----kino'+secrets.token_hex(8); data=Path(p['storage']).read_bytes(); parts=[f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{uid}\r\n'.encode(),f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="attachment"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(),data,f'\r\n--{boundary}--\r\n'.encode()]; req=urllib.request.Request('https://api.telegram.org/bot'+TOKEN+'/sendDocument',data=b''.join(parts),headers={'Content-Type':'multipart/form-data; boundary='+boundary}); result=json.load(urllib.request.urlopen(req,timeout=50))
   except Exception as e:result={'ok':False,'description':str(e)}
  with conn() as c:c.execute('insert or replace into deliveries values (?,?,?)',(post_id,uid,'sent' if result.get('ok') else 'failed'))
  time.sleep(.04)

def handle_update(update):
 msg=update.get('message') or {}; user=msg.get('from') or {}; uid=user.get('id'); chat=msg.get('chat') or {}
 if not uid or chat.get('type')!='private':return
 name=' '.join(x for x in (user.get('first_name',''),user.get('last_name','')) if x).strip() or 'Студент'; text=msg.get('text','').strip()
 with conn() as c:
  c.execute('insert into users(id,name,username,role,joined) values (?,?,?,?,?) on conflict(id) do update set username=excluded.username',(uid,name,user.get('username',''),'admin' if uid in ADMIN_IDS else ('pending' if JOIN_CODE else 'student'),int(time.time())))
  if uid in ADMIN_IDS:c.execute("update users set role='admin' where id=?",(uid,))
 if text.startswith('/start'):
  invite=text.partition(' ')[2].strip()
  with conn() as c:
   role=c.execute('select role from users where id=?',(uid,)).fetchone()['role']
   if role=='pending' and JOIN_CODE and invite!=JOIN_CODE:
    send(uid,'Для доступа нужна пригласительная ссылка от старосты. Попросите её и откройте бота по ссылке.');return
   c.execute("update users set subscribed=1, role=case when role='pending' then 'student' else role end where id=?",(uid,))
  menu={'inline_keyboard':[[{'text':'Открыть приложение','web_app':{'url':BASE}}]]} if BASE else None
  send(uid,'Вы подключены к группе. Здесь приходят объявления и изменения расписания. Откройте приложение, чтобы посмотреть всё в одном месте.',menu)
 elif text.startswith('/login'):
  with conn() as c: role=c.execute('select role from users where id=?',(uid,)).fetchone()['role']
  if role=='pending':send(uid,'Сначала откройте пригласительную ссылку от старосты.');return
  code=f'{secrets.randbelow(1000000):06d}'
  with conn() as c:c.execute('insert into codes values (?,?,?)',(code,uid,int(time.time())+300))
  send(uid,'Код для входа через браузер: <b>'+code+'</b>\nДействует 5 минут. Никому его не пересылайте.')
 elif text.startswith('/mute'):
  with conn() as c:c.execute('update users set subscribed=0 where id=?',(uid,))
  send(uid,'Уведомления выключены. /start — включить снова.')
 elif text.startswith('/invite') and uid in ADMIN_IDS:
  info=api('getMe',{})
  botname=(info.get('result') or {}).get('username')
  if botname and JOIN_CODE:send(uid,'Ссылка для участников группы:\nhttps://t.me/'+botname+'?start='+JOIN_CODE+'\nПерешлите её только своим студентам.')
  else:send(uid,'Не удалось получить ссылку. Проверьте настройки бота.')
 elif text.startswith('/send') and uid in ADMIN_IDS:
  title=text[5:].strip()
  if not title:send(uid,'Для рассылки напишите: /send Текст объявления. Файл можно отправить следующим сообщением с подписью /send Текст.');return
  with conn() as c:pid=c.execute('insert into posts(kind,title,created,author) values (?,?,?,?)',('announcement',title,int(time.time()),uid)).lastrowid
  threading.Thread(target=notify,args=(pid,),daemon=True).start();send(uid,'Опубликовано. Рассылка началась.')
 elif msg.get('document') and uid in ADMIN_IDS and (msg.get('caption') or '').startswith('/send'):
  doc=msg['document']; name=doc.get('file_name','Файл'); size=doc.get('file_size',0)
  if size>MAX_FILE:send(uid,'Файл больше 20 МБ.');return
  info=api('getFile',{'file_id':doc['file_id']})
  if not info.get('ok'):send(uid,'Не удалось получить файл.');return
  path=UP/(secrets.token_hex(16)); url='https://api.telegram.org/file/bot'+TOKEN+'/'+info['result']['file_path']
  try:
   with urllib.request.urlopen(url,timeout=50) as r:path.write_bytes(r.read(MAX_FILE+1))
   if path.stat().st_size>MAX_FILE:path.unlink();send(uid,'Файл больше 20 МБ.');return
   with conn() as c:
    fid=c.execute('insert into files(storage,name,mime,size) values (?,?,?,?)',(str(path),name,mimetypes.guess_type(name)[0] or 'application/octet-stream',path.stat().st_size)).lastrowid
    pid=c.execute('insert into posts(kind,title,file_id,created,author) values (?,?,?,?,?)',('announcement',msg['caption'][5:].strip() or name,fid,int(time.time()),uid)).lastrowid
   threading.Thread(target=notify,args=(pid,),daemon=True).start();send(uid,'Файл опубликован. Рассылка началась.')
  except Exception:send(uid,'Не удалось загрузить файл.')
 elif uid in ADMIN_IDS:send(uid,'Команды: /invite — ссылка для группы; /send текст — объявление всем; /login — вход в браузере; /mute — отключить уведомления.')
 else:send(uid,'Откройте приложение по кнопке меню. /login — вход в браузере; /mute — отключить уведомления.')

def poll():
 offset=0
 while True:
  try:
   result=api('getUpdates',{'offset':offset,'timeout':25,'allowed_updates':['message']})
   for item in result.get('result',[]):
    offset=item['update_id']+1
    try:handle_update(item)
    except Exception as e:print('update:',e,flush=True)
  except Exception as e:print('poll:',e,flush=True)
  time.sleep(2 if not TOKEN else .2)

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def json(self,data,status=200):
  raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
 def fail(self,msg,status=400):self.json({'error':msg},status)
 def body(self):
  size=int(self.headers.get('Content-Length','0'))
  if size>MAX_FILE+1024*1024:raise ValueError('Слишком большой запрос')
  return self.rfile.read(size)
 def user(self):
  auth=self.headers.get('Authorization','')
  if auth.startswith('Bearer '):
   with conn() as c:
    row=c.execute('select u.* from sessions s join users u on u.id=s.user_id where s.token=? and s.expires>?',(auth[7:],int(time.time()))).fetchone()
   return row
  return None
 def admin(self):return self.user() and self.user()['role']=='admin'
 def do_GET(self):
  url=urllib.parse.urlsplit(self.path); path=url.path
  if path=='/health':return self.json({'ok':True})
  if path.startswith('/api/'):
   u=self.user()
   if not u:return self.fail('Войдите через Telegram или код из бота',401)
   with conn() as c:
    if path=='/api/state':
     data={'group':GROUP,'me':dict(u),'posts':[dict(x) for x in c.execute("select p.*,f.name filename from posts p left join files f on p.file_id=f.id where p.expires='' or p.expires>=date('now') order by p.pinned desc,p.created desc limit 100")],'lessons':[dict(x) for x in c.execute('select * from lessons order by weekday,start')],'changes':[dict(x) for x in c.execute("select * from changes where day>=date('now','-7 days') order by day,start")],'teachers':[dict(x) for x in c.execute('select * from teachers order by name')],'resources':[dict(x) for x in c.execute('select * from resources order by id desc')],'students':[dict(x) for x in c.execute("select id,name,username,case when show_phone=1 then phone else '' end phone,role from users order by name")],'subscribers':c.execute('select count(*) from users where subscribed=1').fetchone()[0]}
     return self.json(data)
    if path.startswith('/api/file/'):
     row=c.execute('select * from files where id=?',(path.rsplit('/',1)[-1],)).fetchone()
     if not row:return self.fail('Файл не найден',404)
     data=Path(row['storage']).read_bytes();self.send_response(200);self.send_header('Content-Type',row['mime']);self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(row['name']));self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data);return
   return self.fail('Не найдено',404)
  file=ROOT/'static'/('index.html' if path=='/' else path.lstrip('/'))
  if not file.is_file() or ROOT/'static' not in file.resolve().parents:return self.fail('Не найдено',404)
  data=file.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(file)[0] or 'text/plain');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_POST(self):
  path=urllib.parse.urlsplit(self.path).path
  try:
   if path=='/api/auth':
    payload=json.loads(self.body()); uid=None
    if 'initData' in payload and TOKEN:
     params=dict(urllib.parse.parse_qsl(payload['initData'],keep_blank_values=True)); given=params.pop('hash',''); check='\n'.join(f'{k}={v}' for k,v in sorted(params.items())); secret=hmac.new(b'WebAppData',TOKEN.encode(),hashlib.sha256).digest(); sig=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
     if hmac.compare_digest(sig,given) and abs(time.time()-int(params.get('auth_date','0')))<86400:uid=json.loads(params['user'])['id']
    elif re.fullmatch(r'\d{6}',str(payload.get('code',''))):
     with conn() as c:
      row=c.execute('select * from codes where code=? and expires>?',(payload['code'],int(time.time()))).fetchone()
      if row:uid=row['user_id'];c.execute('delete from codes where code=?',(payload['code'],))
    if not uid:return self.fail('Не удалось подтвердить вход',401)
    with conn() as c:
     existing=c.execute('select role from users where id=?',(uid,)).fetchone()
     if JOIN_CODE and (not existing or existing['role']=='pending') and uid not in ADMIN_IDS:return self.fail('Нужна пригласительная ссылка от старосты',403)
     c.execute('insert or ignore into users(id,name,role,joined) values (?,?,?,?)',(uid,'Студент','admin' if uid in ADMIN_IDS else 'student',int(time.time())))
     token=secrets.token_urlsafe(32);c.execute('insert into sessions values (?,?,?)',(token,uid,int(time.time())+30*86400))
    return self.json({'token':token})
   u=self.user()
   if not u:return self.fail('Войдите в приложение',401)
   if path=='/api/profile':
    p=json.loads(self.body());name=str(p.get('name','')).strip()[:100];phone=str(p.get('phone','')).strip()[:40]
    if not name:return self.fail('Укажите имя')
    with conn() as c:c.execute('update users set name=?,phone=?,show_phone=? where id=?',(name,phone,1 if p.get('show_phone') else 0,u['id']))
    return self.json({'ok':True})
   if not self.admin():return self.fail('Только для администратора',403)
   if path=='/api/upload':
    typ=self.headers.get('Content-Type','')
    if not typ.lower().startswith('multipart/form-data;'):return self.fail('Ожидается файл')
    raw=self.body()
    msg=BytesParser(policy=default).parsebytes(('Content-Type: '+typ+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw)
    if not msg.is_multipart():return self.fail('Неверный формат файла')
    parts=[part for part in msg.iter_parts() if part.get_param('name',header='content-disposition')=='file']
    if len(parts)!=1 or not parts[0].get_filename():return self.fail('Выберите файл')
    name=Path(parts[0].get_filename()).name[:180]
    data=parts[0].get_payload(decode=True)
    if not isinstance(data,bytes):return self.fail('Неверный формат файла')
    if len(data)>MAX_FILE:return self.fail('Файл больше 20 МБ')
    mime=mimetypes.guess_type(name)[0] or 'application/octet-stream'; storage=UP/secrets.token_hex(16);storage.write_bytes(data)
    with conn() as c:fid=c.execute('insert into files(storage,name,mime,size) values (?,?,?,?)',(str(storage),name,mime,len(data))).lastrowid
    return self.json({'id':fid,'name':name})
   p=json.loads(self.body()); table=path.removeprefix('/api/')
   if table not in ('posts','lessons','changes','teachers','resources'):return self.fail('Не найдено',404)
   fields={'posts':['kind','title','body','file_id','pinned','expires'],'lessons':['weekday','start','finish','subject','teacher','room','subgroup'],'changes':['day','lesson_id','subject','start','finish','teacher','room','note','cancelled'],'teachers':['name','subject','contact'],'resources':['title','url']}[table]
   values={k:p.get(k,'') for k in fields};
   if table=='posts':
    if values['kind'] not in ('announcement','deadline','change'):return self.fail('Неверный тип')
    values['pinned']=int(bool(values['pinned']));values['file_id']=int(values['file_id']) if str(values['file_id']).isdigit() else None
   if table=='lessons' and str(values['weekday']) not in map(str,range(7)):return self.fail('Неверный день')
   if table=='changes':values['cancelled']=int(bool(values['cancelled']));values['lesson_id']=int(values['lesson_id']) if str(values['lesson_id']).isdigit() else None
   if not (values.get('title') or values.get('subject') or values.get('name')):return self.fail('Заполните название')
   with conn() as c:
    keys=list(values); extra={'posts':{'created':int(time.time()),'author':u['id']},'changes':{'created':int(time.time())}}.get(table,{})
    values.update(extra);keys=list(values)
    rowid=c.execute(f'insert into {table} ({",".join(keys)}) values ({",".join("?" for _ in keys)})',list(values.values())).lastrowid
   if table=='posts' and p.get('broadcast'):threading.Thread(target=notify,args=(rowid,),daemon=True).start()
   return self.json({'id':rowid})
  except (ValueError,KeyError,sqlite3.Error) as e:return self.fail(str(e))
 def do_DELETE(self):
  u=self.user()
  if not u or u['role']!='admin':return self.fail('Только для администратора',403)
  match=re.fullmatch(r'/api/(posts|lessons|changes|teachers|resources)/(\d+)',urllib.parse.urlsplit(self.path).path)
  if not match:return self.fail('Не найдено',404)
  with conn() as c:c.execute(f'delete from {match[1]} where id=?',(match[2],))
  return self.json({'ok':True})

if __name__=='__main__':
 if TOKEN:threading.Thread(target=poll,daemon=True).start()
 print('Listening on',PORT,flush=True);ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
