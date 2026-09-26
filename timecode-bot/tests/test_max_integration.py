"""MAX and Telegram must share TIMECODE content without sharing external IDs."""
import hashlib
import hmac
import importlib.util
import json
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('timecode_max_test',root/'server.py')
server=importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class MaxIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        server.DB=Path(self.temp.name)/'timecode.db'
        server.SECRET='a'*40
        server.MAX_TOKEN='test-token'
        server.MAX_WEBHOOK_SECRET='test-webhook-secret'
        server.GROUP=''
        server.init()

    def tearDown(self):self.temp.cleanup()

    def signed_data(self,user_id):
        values={'auth_date':str(int(time.time())),'user':json.dumps({'id':user_id})}
        raw='\n'.join(k+'='+v for k,v in sorted(values.items()))
        key=hmac.new(b'WebAppData',server.MAX_TOKEN.encode(),hashlib.sha256).digest()
        values['hash']=hmac.new(key,raw.encode(),hashlib.sha256).hexdigest()
        return urllib.parse.urlencode(values)

    def test_signed_launch_creates_separate_identity(self):
        server.roster(52,'Telegram student')
        self.assertEqual(server.max_user(self.signed_data(52)),-52)
        self.assertEqual(server.user_from_token(server.signed(-52))['id'],-52)
        self.assertEqual(server.user_from_token(server.signed(52))['name'],'Telegram student')
        self.assertIsNone(server.max_user(self.signed_data(52).replace('52','53',1)))

    def test_start_and_keyboard_route_to_max(self):
        with patch.object(server.max_transport,'send_text',return_value={'message':{'body':{'mid':'1'}}}) as delivered:
            server.max_update({'update_type':'bot_started','user':{'user_id':63,'name':'Ученик'}})
        self.assertTrue(server.allowed(-63))
        self.assertEqual(delivered.call_args.args[0],63)
        buttons=delivered.call_args.kwargs['keyboard']
        self.assertTrue(any(button['type']=='open_app' for row in buttons for button in row) if server.BASE else True)

    def test_untrusted_webhook_header_rejected(self):
        self.assertFalse(server.max_transport.valid_webhook_secret('bad',server.MAX_WEBHOOK_SECRET))
        self.assertTrue(server.max_transport.valid_webhook_secret('test-webhook-secret',server.MAX_WEBHOOK_SECRET))

    def test_mission_button_stays_in_max(self):
        rows=server.max_transport.keyboard_from_telegram([[{'text':'Ответить','url':'https://t.me/timecode_bot?start=mission'}]])
        self.assertEqual(rows[0][0]['payload'],'max:start:mission')


if __name__=='__main__':unittest.main()
