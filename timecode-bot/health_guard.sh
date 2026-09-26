#!/usr/bin/env bash
# Restart a live-but-unresponsive bot; never initialize an empty replacement database.
set -euo pipefail
health='http://127.0.0.1:8097/health'
if curl -fsS --max-time 4 "$health" -o /dev/null; then exit 0; fi
sleep 3
if curl -fsS --max-time 4 "$health" -o /dev/null; then exit 0; fi
if ! runuser -u www-data -- python3 - <<'PY'
import sqlite3
c=sqlite3.connect('file:/var/lib/timecode-bot/timecode.db?mode=ro',uri=True,timeout=3)
assert c.execute('select count(*) from users').fetchone()[0]>0
PY
then
    logger -t timecode-guard 'Bot unresponsive; database not verified, refusing restart'
    exit 1
fi
logger -t timecode-guard 'Bot unresponsive twice; restarting service'
systemctl restart timecode-bot.service
for attempt in 1 2 3 4 5; do
    if curl -fsS --max-time 4 "$health" -o /dev/null; then
        logger -t timecode-guard 'Bot recovered and answering health endpoint'
        exit 0
    fi
    sleep 2
done
logger -t timecode-guard 'Bot still unresponsive after restart'
exit 1
