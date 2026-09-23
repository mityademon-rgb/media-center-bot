import hashlib
import hmac
import importlib.util
import json
import os
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'server.py'
spec = importlib.util.spec_from_file_location('timecode_server', MODULE)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class BotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        server.DB = Path(self.temp.name) / 'bot.db'
        server.SECRET = 'a'*40
        server.TOKEN = '123:TEST'
        server.JOIN = 'secret-join-test-1234567890'
        server.ADMINS = {11}
        server.GROUP = '-10042'
        server.init()
        server.roster(11, 'Дмитрий')
        server.roster(42, 'Матвей')

    def tearDown(self):
        self.temp.cleanup()

    def test_init_data_signature_and_expiry(self):
        import time
        pairs = {'auth_date': str(int(time.time())), 'user': json.dumps({'id': 42})}
        check = '\n'.join(k+'='+v for k,v in sorted(pairs.items()))
        key = hmac.new(b'WebAppData', server.TOKEN.encode(), hashlib.sha256).digest()
        pairs['hash'] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
        raw = urllib.parse.urlencode(pairs)
        self.assertEqual(server.telegram_user(raw), 42)
        self.assertIsNone(server.telegram_user(raw.replace('42', '43')))

    def test_digest_only_includes_shared_answers(self):
        with server.conn() as c:
            c.execute('insert into answers(user_id,period,day,choice,detail,published) values (?,?,?,?,?,?)', (42,'am',server.today(),'В кадре','Еду в Москву',1))
            c.execute('insert into answers(user_id,period,day,choice,detail,published) values (?,?,?,?,?,?)', (11,'am',server.today(),'Сонный','Секрет',0))
        with patch.object(server, 'send') as sent, patch.object(server, 'ai_digest', return_value=None):
            server.digest('am')
        message = sent.call_args.args[1]
        self.assertIn('Матвей', message)
        self.assertIn('Москву', message)
        self.assertNotIn('Секрет', message)

    def test_invitation_required(self):
        with patch.object(server, 'send') as sent:
            server.bot_message({'chat': {'type': 'private'}, 'from': {'id': 99, 'first_name': 'Гость'}, 'text': '/start'})
        self.assertFalse(server.allowed(99))
        self.assertIn('приглашению', sent.call_args.args[1])
        with patch.object(server, 'send'):
            server.bot_message({'chat': {'type': 'private'}, 'from': {'id': 99, 'first_name': 'Гость'}, 'text': '/start '+server.JOIN})
        self.assertTrue(server.allowed(99))

    def test_auth_token_tampering(self):
        token = server.signed(42)
        self.assertEqual(server.user_from_token(token)['name'], 'Матвей')
        self.assertIsNone(server.user_from_token(token.replace('42.', '11.', 1)))


if __name__ == '__main__':
    unittest.main()
