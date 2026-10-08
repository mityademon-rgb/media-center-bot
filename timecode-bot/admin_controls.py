"""Keep teacher controls visible and route them before student activities."""

def install(s):
    original_send = s['send']
    original_message = s['bot_message']

    def buttons():
        return [[{'text': '📣 Написать всем', 'callback_data': 'admin:publish'},
                 {'text': '👥 Подписчики', 'callback_data': 'admin:subscribers:0'}],
                [{'text': '📅 Редактировать расписание', 'callback_data': 'admin:schedule'}]]

    def send(chat, text, keyboard=None):
        if chat in s['ADMINS']:
            keyboard = [list(row) for row in (keyboard or [])]
            present = {b.get('callback_data') for row in keyboard for b in row}
            for row in buttons():
                missing = [b for b in row if b['callback_data'] not in present]
                if missing:
                    keyboard.append(missing)
        return original_send(chat, text, keyboard)

    def message(msg):
        uid = (msg.get('from') or {}).get('id')
        text = (msg.get('text') or '').strip()
        if uid in s['ADMINS'] and (msg.get('chat') or {}).get('type') == 'private':
            routes = {'📣 Написать всем': 'admin:publish',
                      '👥 Подписчики': 'admin:subscribers:0',
                      '📅 Расписание': 'admin:schedule',
                      '📅 Редактировать расписание': 'admin:schedule'}
            if text in routes:
                return s['callback']({'id': 'max', 'from': {'id': uid}, 'data': routes[text]})
        return original_message(msg)

    s.update(send=send, bot_message=message)
