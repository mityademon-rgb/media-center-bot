#!/usr/bin/env bash
set -Eeuo pipefail

DOMAIN='group.timecode-lab.ru'
EXPECTED_IP='72.56.65.161'
PORT='8087'
REPO='https://github.com/mityademon-rgb/media-center-bot.git'
BRANCH='feature/kino-group-miniapp'
BASE='/opt/kino-group'
APP="$BASE/kino-group"
CONF='/etc/nginx/sites-available/kino-group.conf'
LINK='/etc/nginx/sites-enabled/kino-group.conf'
UNIT='/etc/systemd/system/kino-group.service'
ENVFILE='/etc/kino-group.env'
WEBROOT='/var/lib/kino-group/acme'
USER_NAME='kino-group'

fail() { echo "ОШИБКА: $*" >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || fail 'Запустите от root.'
for bin in git nginx certbot python3 curl getent ss systemctl; do command -v "$bin" >/dev/null || fail "Не найдена команда $bin. Установка остановлена."; done
python3 - <<'PY' || fail 'Нужен Python 3.12 или новее.'
import sys
assert sys.version_info[:2] >= (3, 12), sys.version
PY
nginx -t || fail 'Существующая конфигурация Nginx не проходит проверку.'
[[ ! -e "$CONF" && ! -e "$LINK" && ! -e "$UNIT" && ! -e "$ENVFILE" ]] || fail 'Файлы приложения уже существуют. Повторная установка остановлена без перезаписи.'
[[ ! -e "$BASE" ]] || fail "Каталог $BASE уже существует. Установка остановлена."
if ss -ltn | awk '{print $4}' | grep -Eq ":${PORT}$"; then fail "Порт $PORT уже занят."; fi
DNS_IPS=$(getent ahostsv4 "$DOMAIN" | awk '{print $1}' | sort -u)
[[ -n "$DNS_IPS" ]] || fail "DNS-запись $DOMAIN ещё не видна с сервера."
echo "$DNS_IPS" | grep -Fxq "$EXPECTED_IP" || fail "DNS $DOMAIN указывает на $DNS_IPS, нужен $EXPECTED_IP."
[[ -d /etc/letsencrypt/live/$DOMAIN ]] && fail 'Для домена уже есть сертификат; установка требует ручной проверки существующей конфигурации.'

echo 'Проверки пройдены. Дальше будут созданы только новые файлы kino-group.'
read -r -p 'Telegram ID старосты (цифры): ' ADMIN_IDS
ADMIN_IDS=$(printf '%s' "$ADMIN_IDS" | tr -d '[:space:]')
[[ "$ADMIN_IDS" =~ ^[0-9]+(,[0-9]+)*$ ]] || fail 'Неверный список ID.'
read -r -s -p 'Токен нового бота от BotFather (не отображается): ' BOT_TOKEN; echo
[[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{20,}$ ]] || fail 'Формат токена неверный.'
BOT_INFO=$(curl -fsS --max-time 15 "https://api.telegram.org/bot${BOT_TOKEN}/getMe") || fail 'Не удалось проверить токен через Telegram.'
BOT_NAME=$(python3 -c 'import json,sys; x=json.load(sys.stdin); assert x.get("ok"); print(x["result"]["username"])' <<< "$BOT_INFO") || fail 'Токен не прошёл проверку.'
read -r -p 'Название группы [КИНО / ГРУППА]: ' GROUP_NAME
GROUP_NAME=${GROUP_NAME:-КИНО / ГРУППА}
JOIN_CODE=$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')
read -r -p 'Email для уведомлений о сертификате: ' EMAIL
[[ "$EMAIL" == *@*.* ]] || fail 'Введите корректный email.'

CREATED_NGINX=0
rollback() {
  status=$?
  if (( status != 0 )); then
    echo 'Установка прервалась. Проверяем, что конфигурация Nginx остаётся рабочей.' >&2
    if (( CREATED_NGINX )); then
      rm -f "$LINK" "$CONF"
      nginx -t >/dev/null 2>&1 && systemctl reload nginx || true
    fi
    systemctl stop kino-group.service >/dev/null 2>&1 || true
    echo "Подготовленные файлы в $BASE сохранены для диагностики. Действующие сайты не удалены." >&2
  fi
}
trap rollback EXIT

git clone --quiet --branch "$BRANCH" --single-branch "$REPO" "$BASE"
[[ -f "$APP/server.py" ]] || fail 'В репозитории не найдено приложение.'
python3 -m py_compile "$APP/server.py"
id "$USER_NAME" >/dev/null 2>&1 || useradd --system --home-dir /var/lib/kino-group --shell /usr/sbin/nologin "$USER_NAME"
install -d -m 750 -o "$USER_NAME" -g "$USER_NAME" /var/lib/kino-group "$APP/data" "$APP/uploads"
install -d -m 755 -o root -g root "$WEBROOT/.well-known/acme-challenge"
chown -R "$USER_NAME:$USER_NAME" "$APP/data" "$APP/uploads"

# Token is written only to the server, never to GitHub or shell history.
export BOT_TOKEN ADMIN_IDS GROUP_NAME JOIN_CODE
python3 - "$ENVFILE" "$DOMAIN" "$PORT" "$APP" <<'PY'
import os,sys
path,domain,port,app=sys.argv[1:]
token=os.environ["BOT_TOKEN"]; admins=os.environ["ADMIN_IDS"]; group=os.environ["GROUP_NAME"]; join_code=os.environ["JOIN_CODE"]
from shlex import quote
with open(path,'x') as f:
 for key,val in dict(BOT_TOKEN=token,ADMIN_IDS=admins,GROUP_NAME=group,JOIN_CODE=join_code,PUBLIC_URL='https://'+domain,PORT=port,DATA_DIR=app+'/data',UPLOAD_DIR=app+'/uploads').items():
  f.write(f'{key}={quote(val)}\n')
os.chmod(path,0o600)
PY

cat > "$UNIT" <<EOF
[Unit]
Description=Cinema group Telegram bot and mini app
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$APP
EnvironmentFile=$ENVFILE
ExecStart=/usr/bin/python3 $APP/server.py
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$APP/data $APP/uploads
PrivateTmp=true
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now kino-group.service
sleep 2
curl -fsS --max-time 5 "http://127.0.0.1:$PORT/health" >/dev/null || fail 'Приложение не ответило на проверку.'

# Initial HTTP vhost serves ACME challenge, and does not touch existing vhosts.
cat > "$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; }
    location / { proxy_pass http://127.0.0.1:$PORT; proxy_set_header Host \$host; }
}
EOF
ln -s "$CONF" "$LINK"
CREATED_NGINX=1
nginx -t || fail 'Новая HTTP-конфигурация не прошла проверку.'
systemctl reload nginx
certbot certonly --webroot --non-interactive --agree-tos --email "$EMAIL" -w "$WEBROOT" -d "$DOMAIN" || fail 'Не удалось выпустить сертификат. Проверьте DNS и доступ к порту 80.'

cat > "$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name $DOMAIN;
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    client_max_body_size 21m;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
nginx -t || fail 'Новая HTTPS-конфигурация не прошла проверку.'
systemctl reload nginx
curl -fsS --max-time 15 "https://$DOMAIN/health" >/dev/null || fail 'HTTPS не ответил на проверку.'

# Menu button is configured only after HTTPS passes.
curl -fsS --max-time 15 -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton" \
  --data-urlencode 'menu_button={"type":"web_app","text":"Открыть группу","web_app":{"url":"https://'"$DOMAIN"'"}}' >/dev/null || echo 'Кнопку меню не удалось настроить автоматически; сайт работает.' >&2
trap - EXIT
echo "ГОТОВО: https://$DOMAIN/"
echo "БОТ: https://t.me/$BOT_NAME"
echo "ПРИГЛАШЕНИЕ ДЛЯ СТУДЕНТОВ: https://t.me/$BOT_NAME?start=$JOIN_CODE"
echo "СЛУЖБА: systemctl status kino-group.service"
echo 'Староста и участники должны открыть бот и нажать /start. Староста входит через /login либо из Telegram.'
