"""Independent TIMECODE guard: health, missed editions, retry alerts."""
import datetime as dt
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

DB = Path(os.getenv('DATABASE', '/var/lib/timecode-bot/timecode.db'))
STATE = DB.parent / 'watchdog-state.json'
TZ = ZoneInfo('Europe/Moscow')
TOKEN = os.getenv('BOT_TOKEN', '')
ADMINS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()]
ROOT = Path(__file__).resolve().parent


def command(*args, timeout=12):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def health():
    try:
        if command('systemctl', 'is-active', '--quiet', 'timecode-bot.service').returncode:
            return False
        with urllib.request.urlopen('http://127.0.0.1:8097/health', timeout=4) as response:
            return response.status == 200
    except Exception:
        return False


def file_descriptors():
    try:
        pid = int(command('systemctl', 'show', '-p', 'MainPID', '--value', 'timecode-bot.service').stdout.strip())
        return len(os.listdir('/proc/' + str(pid) + '/fd')) if pid > 0 else 0
    except Exception:
        return 0


def notify(message):
    if not TOKEN or not ADMINS:
        return False
    delivered = True
    for chat in ADMINS:
        try:
            response = command('curl', '-4', '-fsS', '--connect-timeout', '5', '--max-time', '12',
                '-H', 'Content-Type: application/json', '--data-binary',
                json.dumps({'chat_id':chat,'text':'Сторож TIMECODE: '+message},ensure_ascii=False),
                'https://api.telegram.org/bot'+TOKEN+'/sendMessage', timeout=15)
            delivered = delivered and response.returncode == 0 and json.loads(response.stdout).get('ok') is True
        except Exception:
            delivered = False
    return delivered


def load():
    try:return json.loads(STATE.read_text())
    except (OSError,ValueError):return {'alerts':{},'last_restart':0,'public_failures':0}


def save(state):
    STATE.parent.mkdir(parents=True,exist_ok=True)
    temp=STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(state,ensure_ascii=False))
    temp.chmod(0o600)
    temp.replace(STATE)


def alert(state,key,message):
    key=dt.datetime.now(TZ).date().isoformat()+':'+key
    if state.setdefault('alerts',{}).get(key):return
    if notify(message):state['alerts'][key]=int(time.time())
    else:print('Alert delivery failed:',key,flush=True)


def missing_and_pending(day):
    if not DB.is_file():return [],0
    now=dt.datetime.now(TZ)
    schedule=[('digest-am','10:00'),('tip','15:00'),('digest-pm','20:30')]
    with sqlite3.connect(DB,timeout=5) as c:
        slots={row[0] for row in c.execute('select slot from sent where day=?',(day,))}
        missing=[(slot,at) for slot,at in schedule if slot not in slots and
                 now>dt.datetime.combine(now.date(),dt.time.fromisoformat(at),TZ)+dt.timedelta(minutes=12)]
        try:
            pending=c.execute('select count(*) from notification_outbox where day=? and delivered=0',(day,)).fetchone()[0]
            pending+=c.execute('select count(*) from notification_photo_outbox where day=? and delivered=0',(day,)).fetchone()[0]
        except sqlite3.OperationalError:
            pending=0
    return missing,pending


def public_healthy():
    try:return command('curl','-fsS','--connect-timeout','4','--max-time','8',
                       'https://timecode-lab.ru/tc/','-o','/dev/null',timeout=10).returncode==0
    except Exception:return False


def main():
    state=load();now=dt.datetime.now(TZ);day=now.date().isoformat()
    healthy=health();fds=file_descriptors() if healthy else 0
    if not healthy or fds>250:
        reason='нет ответа приложения' if not healthy else 'растёт число открытых файлов ('+str(fds)+')'
        if time.time()-state.get('last_restart',0)>600:
            state['last_restart']=int(time.time());save(state)
            command('systemctl','restart','timecode-bot.service',timeout=35)
            for _ in range(5):
                time.sleep(2)
                if health():break
            if health():alert(state,'restart-'+reason,'обнаружил сбой: '+reason+'. Перезапустил службу, она отвечает.')
            else:alert(state,'down','бот не отвечает после автоматического перезапуска: '+reason)
        elif not healthy:alert(state,'down','бот не отвечает. Повторный перезапуск временно ограничен.')
    if not public_healthy():
        state['public_failures']=state.get('public_failures',0)+1
        if state['public_failures']>=2:alert(state,'public','адрес приложения https://timecode-lab.ru/tc/ недоступен извне.')
    else:state['public_failures']=0
    try:
        missing,pending=missing_and_pending(day)
        for slot,at in missing:
            deadline=dt.datetime.combine(now.date(),dt.time.fromisoformat(at),TZ)
            if now-deadline<dt.timedelta(hours=2) and health():
                try:
                    import server
                    jobs={'digest-am':lambda:server.digest('am'),'tip':server.tip,'digest-pm':lambda:server.digest('pm')}
                    server.run_slot(slot,jobs[slot])
                except Exception as error:print('Catch-up failed:',slot,type(error).__name__,flush=True)
            still_missing,_=missing_and_pending(day)
            if any(x[0]==slot for x in still_missing):
                alert(state,'missed-'+slot,'пропущен выпуск '+at+' ('+slot+'). Автоматическая попытка восстановления не помогла.')
        if pending and now.time()>=dt.time(20,45):
            alert(state,'pending-outbox','осталось недоставленных сообщений: '+str(pending)+'. Бот повторяет отправку.')
    except Exception as error:
        alert(state,'database','не удалось проверить выпуски и очередь доставки: '+type(error).__name__)
    save(state)


if __name__=='__main__':main()
