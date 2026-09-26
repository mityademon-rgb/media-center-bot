"""Add the screenplay workshop to a live TIMECODE instance without replacing locally edited files."""
from pathlib import Path
import py_compile
import sys

root=Path('/opt/timecode-bot/timecode-bot')
source=Path(sys.argv[1])
server=root/'server.py'
index=root/'static/index.html'

def insert_once(path,marker,addition):
    content=path.read_text()
    if addition in content:return
    if content.count(marker)!=1:raise RuntimeError(f'Unexpected anchor in {path}: {marker[:60]}')
    path.write_text(content.replace(marker,addition+marker,1))

insert_once(server,'import quest_engine as quests','import screenplay_coach as screenplay\n')
insert_once(server,"        if path=='/api/state':",'''        if path=='/api/screenplay':
            u=self.identity()
            if not u:return self.out({'error':'Войдите через Telegram'},401)
            query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            try:project_id=int(query['id'][0]) if 'id' in query else None
            except (ValueError,IndexError):return self.out({'error':'Неверный номер проекта'},400)
            with conn() as c:return self.out(screenplay.data(c,u['id'],project_id))
''')
insert_once(server,"        if path=='/api/profile':",'''        if path=='/api/screenplay':
            try:
                with conn() as c:result=screenplay.act(c,u['id'],p,ai_json)
                return self.out(result)
            except ValueError as error:return self.out({'error':str(error)},400)
''')
content=server.read_text()
if "'/screenplay.js'" not in content:
    marker="'/games-day.webp'"
    if content.count(marker)!=1:raise RuntimeError('Unexpected static file whitelist')
    server.write_text(content.replace(marker,marker+",'/screenplay.js','/screenplay.css'",1))
insert_once(index,'</head>','<link rel="stylesheet" href="screenplay.css">')
insert_once(index,'</body>','<script src="screenplay.js"></script>')
for name in ('screenplay.js','screenplay.css'):
    (root/'static'/name).write_bytes((source/name).read_bytes())
(root/'screenplay_coach.py').write_bytes((source/'screenplay_coach.py').read_bytes())
py_compile.compile(str(server),doraise=True)
py_compile.compile(str(root/'screenplay_coach.py'),doraise=True)
