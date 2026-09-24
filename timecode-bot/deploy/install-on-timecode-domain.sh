#!/usr/bin/env bash
# Run once on the existing TIMECODE server as root, from a terminal.
set -euo pipefail

repo='https://github.com/mityademon-rgb/media-center-bot.git'
branch='feature/timecode-media-bot'
target='/opt/timecode-bot'
nginx_site='/etc/nginx/conf.d/boom-kadr.conf'
unit='/etc/systemd/system/timecode-bot.service'
env_file='/etc/timecode-bot.env'
data_dir='/var/lib/timecode-bot'
backup="${nginx_site}.timecode-backup-$(date +%Y%m%d%H%M%S)"
url='https://timecode-lab.ru/tc/'
changed_nginx=0
started_service=0

fail() { echo "ОШИБКА: $*" >&2; exit 1; }
rollback() {
  code=$?
  trap - EXIT
  if (( code != 0 )); then
    if (( changed_nginx )); then
      cp -p "$backup" "$nginx_site"
      if nginx -t; then systemctl reload nginx || true; fi
    fi
    if (( started_service )); then systemctl stop timecode-bot.service || true; fi
    echo "Установка прервана. Исходный Nginx восстановлен; файлы проекта и закрытые ключи сохранены для диагностики." >&2
  fi
  exit "$code"
}
trap rollback EXIT

[[ $EUID == 0 && -t 0 ]] || fail 'Нужен терминал root для безопасного ввода ключей.'
[[ -f "$nginx_site" ]] || fail 'Нужный конфиг сайта не найден.'
[[ ! -e "$target" && ! -e "$unit" && ! -e "$env_file" && ! -e "$data_dir" ]] || fail 'Файлы TIMECODE уже существуют. Повторную установку автоматически не выполняем.'
[[ -f /etc/letsencrypt/live/timecode-lab.ru/fullchain.pem ]] || fail 'Сертификат timecode-lab.ru не найден.'
! grep -q 'TIMECODE-MINIAPP-BEGIN' "$nginx_site" || fail 'Маршрут /tc/ уже установлен.'
! grep -Eq 'location[[:space:]]+[^[:space:]]*[[:space:]]*/tc(/|[[:space:]]|\{)' "$nginx_site" || fail 'Путь /tc/ уже занят.'
! ss -ltn '( sport = :8097 )' | grep -q ':8097' || fail 'Порт 8097 занят.'
nginx -t
command -v git >/dev/null && command -v python3 >/dev/null && command -v curl >/dev/null || fail 'Нужны git, python3, curl.'
python3 -c 'import sys; assert sys.version_info >= (3,12)' || fail 'Нужен Python 3.12+.'

read -r -p 'Telegram ID преподавателя [7103097249]: ' admin_id
admin_id=${admin_id:-7103097249}
[[ $admin_id =~ ^[0-9]{6,20}$ ]] || fail 'Telegram ID должен состоять из цифр.'
read -r -s -p 'Токен НОВОГО бота Telegram (не показывается): ' bot_token
echo
read -r -s -p 'API-ключ Kimi (не показывается): ' kimi_key
echo
[[ $bot_token =~ ^[0-9]+:[A-Za-z0-9_-]+$ && $kimi_key =~ ^[A-Za-z0-9_-]{15,}$ ]] || fail 'Проверь токен бота и ключ Kimi.'

# Validation is read-only; errors do not print secrets.
BOT_TOKEN="$bot_token" python3 - <<'PY' || fail 'BotFather-токен не прошёл проверку getMe.'
import json,os,urllib.request
try:
    req=urllib.request.Request('https://api.telegram.org/bot'+os.environ['BOT_TOKEN']+'/getMe')
    with urllib.request.urlopen(req,timeout=15) as r: data=json.load(r)
except Exception:
    raise SystemExit(1)
if not data.get('ok') or not data.get('result',{}).get('username'):raise SystemExit(1)
print('Telegram-бот подтверждён: @'+data['result']['username'])
PY

git clone --depth 1 --branch "$branch" "$repo" "$target"
[[ -f "$target/timecode-bot/server.py" && -f "$target/timecode-bot/deploy/timecode-bot.service" ]] || fail 'Неожиданная структура репозитория.'
install -d -m 0700 -o www-data -g www-data "$data_dir"
install -m 0644 "$target/timecode-bot/deploy/timecode-bot.service" "$unit"

# EnvironmentFile is read by systemd; never source it in an interactive shell.
SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
JOIN_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')
umask 077
cat > "$env_file" <<EOF
BOT_TOKEN=$bot_token
MOONSHOT_API_KEY=$kimi_key
ADMIN_IDS=$admin_id
BASE_URL=$url
JOIN_SECRET=$JOIN_SECRET
SECRET=$SECRET
DATABASE=$data_dir/timecode.db
PORT=8097
KIMI_MODEL=kimi-k2.6
EOF
chmod 600 "$env_file"
unset bot_token kimi_key SECRET JOIN_SECRET

systemctl daemon-reload
started_service=1
systemctl enable --now timecode-bot.service
for attempt in 1 2 3 4 5; do
  if curl -fsS --max-time 3 http://127.0.0.1:8097/health >/dev/null; then break; fi
  sleep 2
done
curl -fsS --max-time 4 http://127.0.0.1:8097/health >/dev/null || fail 'Служба не отвечает локально: смотри journalctl -u timecode-bot -n 30.'

cp -p "$nginx_site" "$backup"
changed_nginx=1
NGINX_SITE="$nginx_site" python3 - <<'PY' || fail 'Не удалось безопасно добавить маршрут в конфигурацию Nginx.'
import os,re
from pathlib import Path
path=Path(os.environ['NGINX_SITE']); content=path.read_text()
matches=[]
for m in re.finditer(r'(?m)^\s*server\s*\{',content):
    start=m.end(); depth=1; pos=start
    while pos<len(content) and depth:
        if content[pos]=='{':depth+=1
        elif content[pos]=='}':depth-=1
        pos+=1
    if depth:raise SystemExit('Незакрытый блок server')
    block=content[start:pos-1]
    if re.search(r'(?m)^\s*listen\s+[^;]*:443\s+ssl\s*;',block) and re.search(r'(?m)^\s*server_name\s+timecode-lab\.ru\s*;',block):
        matches.append((m.end(),pos))
if len(matches)!=1:raise SystemExit('Ожидался ровно один HTTPS-блок timecode-lab.ru; найдено '+str(len(matches)))
position=matches[0][0]
route='''
    # TIMECODE-MINIAPP-BEGIN
    location = /tc { return 302 /tc/; }
    location ^~ /tc/ {
        proxy_pass http://127.0.0.1:8097/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    # TIMECODE-MINIAPP-END
'''
path.write_text(content[:position]+route+content[position:])
PY
nginx -t
systemctl reload nginx
curl -fsS --max-time 12 --resolve timecode-lab.ru:443:217.149.24.234 "$url" -o /dev/null || fail 'Mini App не открылось по HTTPS.'
curl -sS --max-time 12 --resolve timecode-lab.ru:443:217.149.24.234 "${url}api/state" -o /dev/null -w '%{http_code}' | grep -qx '401' || fail 'Проверка авторизации Mini App не пройдена.'
echo "ГОТОВО: $url"
echo 'Открой нового бота и отправь /start. Добавь бота в общий чат и напиши там /connect.'
echo "Резервная копия Nginx: $backup"
