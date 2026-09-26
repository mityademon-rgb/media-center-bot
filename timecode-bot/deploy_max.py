"""Apply the MAX gateway to the live TIMECODE service without replacing local changes."""
from pathlib import Path
import sys

source=Path(sys.argv[1])
root=Path(__file__).resolve().parent

def replace_unique(path,old,new):
    value=path.read_text()
    if value.count(old)!=1:
        raise RuntimeError('Unexpected deployment anchor: '+str(path)+' / '+old[:55])
    path.write_text(value.replace(old,new,1))

live=root/'server.py'
new=(source/'server.py').read_text()
replace_unique(live,'import screenplay_coach as screenplay\n','import screenplay_coach as screenplay\nimport max_transport\n')
replace_unique(live,"TOKEN = os.getenv('BOT_TOKEN', '')\n", "TOKEN = os.getenv('BOT_TOKEN', '')\nMAX_TOKEN = os.getenv('MAX_BOT_TOKEN', '')\nMAX_WEBHOOK_SECRET = os.getenv('MAX_WEBHOOK_SECRET', '')\n")
start='def send(chat, text, keyboard=None):\n'; end="    payload = {'chat_id':chat, 'text':text, 'parse_mode':'HTML'"
replace_unique(live,start+end,new[new.index(start):new.index(end,new.index(start))]+end)
replace_unique(live,"    api('answerCallbackQuery',{'callback_query_id':q['id']})", "    if q['id']!='max':api('answerCallbackQuery',{'callback_query_id':q['id']})")
replace_unique(live,"    if data in ('onboard:lab:kids','onboard:lab:media'):\n", new[new.index("    if q['id']=='max' and data in ('max:start:mission','max:start:instant'):"):new.index("    if data in ('onboard:lab:kids','onboard:lab:media'):")]+"    if data in ('onboard:lab:kids','onboard:lab:media'):\n")
start='def max_user(raw):\n';end='def code_rate_limit(ip):\n'
replace_unique(live,end,new[new.index(start):new.index(end,new.index(start))]+end)
start="        if path=='/api/max/webhook':\n";end="        if path=='/api/auth':\n"
replace_unique(live,end,new[new.index(start):new.index(end,new.index(start))]+end)
replace_unique(live,"            uid=telegram_user(p.get('initData','')) if p.get('initData') else None", "            uid=max_user(p.get('maxInitData','')) if p.get('maxInitData') else telegram_user(p.get('initData','')) if p.get('initData') else None")
(root/'max_transport.py').write_bytes((source/'max_transport.py').read_bytes())
html=root/'static/index.html'
replace_unique(html,'<script src="https://telegram.org/js/telegram-web-app.js"></script>', '<script src="https://telegram.org/js/telegram-web-app.js"></script><script src="https://st.max.ru/js/max-web-app.js"></script>')
js=root/'static/app.js'
replace_unique(js,"const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();let auth=localStorage.getItem('timecode-auth')||''", "const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();const maxApp=window.WebApp;const isMax=!!maxApp?.initData&&!tg?.initData;const authKey=isMax?'timecode-auth-max':'timecode-auth';let auth=localStorage.getItem(authKey)||''")
replace_unique(js,"В Telegram открой приглашение в бот и нажми «Открыть TIMECODE». Для входа через браузер запроси у бота командой", "Открой TIMECODE через своего бота. Для входа через браузер запроси у бота командой")
value=js.read_text()
if value.count("localStorage.setItem('timecode-auth',auth)")!=2 or value.count("localStorage.removeItem('timecode-auth')")!=1:raise RuntimeError('Auth storage changed')
value=value.replace("localStorage.setItem('timecode-auth',auth)","localStorage.setItem(authKey,auth)")
value=value.replace("localStorage.removeItem('timecode-auth')","localStorage.removeItem(authKey)")
js.write_text(value)
replace_unique(js,"if(tg?.initData)try{let r=await req('auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({initData:tg.initData})})", "if(maxApp?.initData||tg?.initData)try{let r=await req('auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(isMax?{maxInitData:maxApp.initData}:{initData:tg.initData})})")
