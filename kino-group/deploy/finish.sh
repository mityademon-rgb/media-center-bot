#!/usr/bin/env bash
set -Eeuo pipefail
DOMAIN='group.timecode-lab.ru'
PORT='8087'
CONF='/etc/nginx/sites-available/kino-group.conf'
LINK='/etc/nginx/sites-enabled/kino-group.conf'
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
ENVFILE='/etc/kino-group.env'
fail(){ echo "ОШИБКА: $*" >&2; exit 1; }
[[ $(id -u) == 0 ]] || fail 'Запустите от root.'
[[ -f "$CERT" && -f "$KEY" ]] || fail "Нет сертификата для $DOMAIN. Сначала выпустите его через DNS-проверку Certbot."
[[ -f "$ENVFILE" && -f /etc/systemd/system/kino-group.service ]] || fail 'Первая стадия установки отсутствует.'
[[ ! -e "$CONF" && ! -e "$LINK" ]] || fail 'Конфигурация kino-group уже существует. Ничего не перезаписываем.'
nginx -t || fail 'Текущая конфигурация Nginx содержит ошибку.'
systemctl start kino-group.service
sleep 2
curl -fsS --max-time 5 "http://127.0.0.1:$PORT/health" >/dev/null || fail 'Служба не отвечает на локальном порту.'
rollback(){ status=$?; if (( status != 0 )); then rm -f "$LINK" "$CONF"; nginx -t >/dev/null 2>&1 && systemctl reload nginx || true; echo 'Новый vhost убран. Действующие сайты не изменены.' >&2; fi; }
trap rollback EXIT
cat > "$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
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
ln -s "$CONF" "$LINK"
nginx -t || fail 'Новая конфигурация не прошла проверку.'
systemctl reload nginx
curl -fsS --max-time 15 "https://$DOMAIN/health" >/dev/null || fail 'Публичный HTTPS не ответил. Проверьте доступность порта 443.'
# Keep the token in the environment; do not print its value.
set -a
# shellcheck disable=SC1090
source "$ENVFILE"
set +a
RESPONSE=$(curl -fsS --max-time 15 -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton" --data-urlencode 'menu_button={"type":"web_app","text":"Открыть группу","web_app":{"url":"https://'"$DOMAIN"'"}}') || fail 'Telegram не принял кнопку меню.'
python3 -c 'import json,sys; assert json.load(sys.stdin).get("ok")' <<< "$RESPONSE" || fail 'Telegram вернул ошибку при установке кнопки меню.'
BOT_INFO=$(curl -fsS --max-time 15 "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
BOT_NAME=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["username"])' <<< "$BOT_INFO")
trap - EXIT
echo "ГОТОВО: https://$DOMAIN/"
echo "БОТ: https://t.me/$BOT_NAME"
echo "ПРИГЛАШЕНИЕ: https://t.me/$BOT_NAME?start=$JOIN_CODE"
echo 'ВАЖНО: сертификат выпущен ручной DNS-проверкой. Для автоматического продления нужен DNS API провайдера; иначе продлить вручную до истечения срока.'
