"""Patch a live checkout without replacing locally modified bot handlers."""
from pathlib import Path
import py_compile
import shutil
import sys

root = Path('/opt/timecode-bot/timecode-bot')
source = Path(sys.argv[1])
server = root / 'server.py'
index = root / 'static/index.html'

def insert(path, marker, addition):
    content = path.read_text()
    if addition in content:
        return
    if content.count(marker) != 1:
        raise RuntimeError('Deployment anchor changed in ' + str(path) + ': ' + marker[:80])
    path.write_text(content.replace(marker, addition + marker, 1))

insert(server, 'import max_transport\n', 'import script_editor\n')
insert(server, '        quests.install(c)\n', '        script_editor.install(c)\n')  # order independent
insert(server, '            class_reminders()\n', "            if t.minute%5==0 and t.second<20:\n                with conn() as c:script_editor.retry(c,DB,ADMINS,TOKEN)\n")
content = server.read_text()
old = '    def body(self):\n        length=int(self.headers.get(\'Content-Length\',\'0\'))\n        if length>100000:return None'
new = '    def body(self, max_size=100000):\n        length=int(self.headers.get(\'Content-Length\',\'0\'))\n        if length<0 or length>max_size:return None'
if old not in content and new not in content:raise RuntimeError('Body limit anchor changed')
content=content.replace(old,new,1)
old = "        path=urllib.parse.urlsplit(self.path).path;p=self.body()"
new = "        path=urllib.parse.urlsplit(self.path).path\n        if path=='/api/script-editor' and not self.identity():return self.out({'error':'Сначала войдите'},401)\n        p=self.body(2_900_000 if path=='/api/script-editor' else 100000)"
if old not in content and new not in content:raise RuntimeError('POST anchor changed')
content=content.replace(old,new,1)
server.write_text(content)
source_code=(source/'server.py').read_text()
start="        if path=='/api/script-editor':\n            try:\n                with conn() as c:result=script_editor.submit"
end="        if path=='/api/profile':"
if start not in server.read_text():
    insert(server,end,source_code[source_code.index(start):source_code.index(end,source_code.index(start))])
content=server.read_text()
old="'/screenplay.js','/screenplay.css'"
new="'/screenplay.js','/screenplay.css','/script_editor.js','/script_editor.css'"
if new not in content:
    if old not in content:raise RuntimeError('Static route anchor changed')
    content=content.replace(old,new,1)
server.write_text(content)
content=index.read_text()
if 'src="intro.mp4" playsinline' not in content and 'src="intro.mp4" autoplay playsinline' not in content:
    raise RuntimeError('Intro video anchor changed')
content=content.replace('src="intro.mp4" playsinline','src="intro.mp4" autoplay playsinline',1)
if 'script_editor.css' not in content:
    if '<link rel="stylesheet" href="intro.css">' not in content:raise RuntimeError('CSS anchor changed')
    content=content.replace('<link rel="stylesheet" href="intro.css">','<link rel="stylesheet" href="intro.css"><link rel="stylesheet" href="script_editor.css">',1)
if 'script_editor.js' not in content:
    if '<script src="screenplay.js"></script>' not in content:raise RuntimeError('JS anchor changed')
    content=content.replace('<script src="screenplay.js"></script>','<script src="screenplay.js"></script><script src="script_editor.js"></script>',1)
index.write_text(content)
for name in ('intro.js','script_editor.js','script_editor.css'):
    shutil.copy2(source/'static'/name,root/'static'/name)
shutil.copy2(source/'script_editor.py',root/'script_editor.py')
py_compile.compile(str(server),doraise=True)
py_compile.compile(str(root/'script_editor.py'),doraise=True)
print('Intro autoplay and script editor installed')
