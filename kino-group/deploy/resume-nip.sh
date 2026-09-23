#!/usr/bin/env bash
set -Eeuo pipefail
DOMAIN='group.217-149-24-234.nip.io'
IP='217.149.24.234'
PORT=8087
CONF='/etc/nginx/sites-available/kino-group.conf'
LINK='/etc/nginx/sites-enabled/kino-group.conf'
ENVFILE='/etc/kino-group.env'
WEBROOT='/var/www/kino-group-acme'
fail(){ echo "ОШИБКА: $*" >&2; exit 1; }
[[ $(id -u) == 0 ]] || fail 'Запустите от root.'
for bin in nginx certbot curl getent systemctl python3; do command -v "$bin" >/dev/null || fail "Не найдена команда $bin"; done
[[ -f "$ENVFILE" && -f /etc/systemd/system/kino-group.service ]] || fail 'Подготовленная служба отсутствует.'
[[ -d /opt/kino-group/kino-group ]] || fail 'Код приложения не найден.'
[[ ! -e "$CONF" && ! -e "$LINK" ]] || fail 'Конфигурация приложения уже существует. Ничего не перезаписываем.'
nginx -t || fail 'Существующая конфигурация Nginx не проходит проверку.'
RESOLVED=$(getent ahostsv4 "$DOMAIN" | awk '{print $1}' | sort -u)
[[ " $RESOLVED " == *" $IP "* ]] || fail "DNS $DOMAIN не указывает на $IP с этого сервера."
install -d -m 755 -o root -g root "$WEBROOT/.well-known/acme-challenge"
# A temporary vhost accepts ACME HTTP-01. No existing vhosts are modified.
cat > "$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    add_header X-Kino-Vhost "kino-acme" always;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; }
    location / { return 404; }
}
EOF
ln -s "$CONF" "$LINK"
rollback(){ status=$?; if (( status != 0 )); then rm -f "$LINK" "$CONF"; nginx -t >/dev/null 2>&1 && systemctl reload nginx || true; echo 'Новый vhost убран; остальные сайты не изменены.' >&2; fi; }
trap rollback EXIT
nginx -t || fail 'Новый временный vhost не прошёл проверку.'
systemctl reload nginx
PROBE="probe-$(date +%s)-$$"
printf '%s\n' "$PROBE" > "$WEBROOT/.well-known/acme-challenge/$PROBE"
PROBE_URL="http://$DOMAIN/.well-known/acme-challenge/$PROBE"
PROBE_HEADERS=$(mktemp)
PROBE_REPLY=$(curl -sS --max-time 8 --noproxy '*' --resolve "$DOMAIN:80:$IP" -D "$PROBE_HEADERS" "$PROBE_URL") || true
if [[ "$PROBE_REPLY" != "$PROBE" ]]; then
    echo "Диагностика: ожидали $PROBE; получили: ${PROBE_REPLY:0:120}" >&2
    cat "$PROBE_HEADERS" >&2
    echo 'Права доступа к файлу:' >&2
    namei -l "$WEBROOT/.well-known/acme-challenge/$PROBE" >&2 || true
    echo 'Последние ошибки Nginx:' >&2
    tail -n 12 /var/log/nginx/error.log >&2 || true
    echo 'Проверка расположения временного vhost:' >&2
    nginx -T 2>/dev/null | grep -n -A 8 -B 3 "server_name $DOMAIN" | head -n 40 >&2 || true
    rm -f "$PROBE_HEADERS"
    fail 'Пробный файл не отдан. Сертификат пока не запрашиваем.'
fi
rm -f "$PROBE_HEADERS"
rm -f "$WEBROOT/.well-known/acme-challenge/$PROBE"
echo 'Проверочный файл доступен по HTTP; запрашиваем сертификат.'
read -r -p 'Email для уведомлений о сертификате [d-d-v@mail.ru]: ' EMAIL
EMAIL=${EMAIL:-d-d-v@mail.ru}
[[ "$EMAIL" == *@*.* ]] || fail 'Некорректный email.'
certbot certonly --webroot --non-interactive --agree-tos --email "$EMAIL" -w "$WEBROOT" -d "$DOMAIN" || fail 'Проверка сертификата не прошла. Существующие сайты не затронуты.'
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
[[ -s "$CERT" && -s "$KEY" ]] || fail 'Файлы сертификата не найдены.'
# Bind only the actual web IP; other HTTPS listeners are left untouched.
cat > "$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen $IP:443 ssl;
    server_name $DOMAIN;
    ssl_certificate $CERT;
    ssl_certificate_key $KEY;
    client_max_body_size 21m;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
nginx -t || fail 'HTTPS-конфигурация не прошла проверку.'
systemctl reload nginx
# Adjust only the application's own environment file after Nginx and certificate work.
python3 - "$ENVFILE" "$DOMAIN" <<'PY'
import os,sys
from shlex import quote
path,domain=sys.argv[1:]
lines=open(path).read().splitlines()
assert sum(line.startswith('PUBLIC_URL=') for line in lines)==1
lines=[f'PUBLIC_URL={quote("https://"+domain)}' if line.startswith('PUBLIC_URL=') else line for line in lines]
tmp=path+'.new'
with open(tmp,'x') as f:f.write('\n'.join(lines)+'\n')
os.chmod(tmp,0o600)
os.replace(tmp,path)
PY
systemctl restart kino-group.service
sleep 2
curl -fsS --max-time 5 "http://127.0.0.1:$PORT/health" >/dev/null || fail 'Служба не ответила локально.'
curl -fsS --max-time 15 --resolve "$DOMAIN:443:$IP" "https://$DOMAIN/health" >/dev/null || fail 'HTTPS не ответил через нужный IP.'
set -a
# shellcheck disable=SC1090
source "$ENVFILE"
set +a
RESPONSE=$(curl -fsS --max-time 15 -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton" --data-urlencode 'menu_button={"type":"web_app","text":"Открыть группу","web_app":{"url":"https://'"$DOMAIN"'"}}') || fail 'Не удалось связаться с Telegram для кнопки меню.'
python3 -c 'import json,sys; assert json.load(sys.stdin).get("ok")' <<< "$RESPONSE" || fail 'Telegram не принял кнопку меню.'
INFO=$(curl -fsS --max-time 15 "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
NAME=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["username"])' <<< "$INFO")
trap - EXIT
echo "ПРИЛОЖЕНИЕ: https://$DOMAIN/"
echo "БОТ: https://t.me/$NAME"
echo "ПРИГЛАШЕНИЕ ДЛЯ ГРУППЫ: https://t.me/$NAME?start=$JOIN_CODE"
echo 'Статус: systemctl status kino-group.service'
