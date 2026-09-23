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

    def test_admin_connects_group(self):
        server.GROUP = ''
        with patch.object(server, 'send'):
            server.bot_message({'chat': {'type': 'supergroup','id':-10042}, 'from': {'id':11}, 'text':'/connect'})
        self.assertEqual(server.GROUP, '-10042')
        server.GROUP = ''
        server.init()
        self.assertEqual(server.GROUP, '-10042')

    def test_tip_falls_back_when_ai_unavailable(self):
        with patch.object(server,'make_daily',return_value=server.fallback_content('tip')),patch.object(server,'send') as sent:
            server.tip()
        text=sent.call_args.args[1]
        self.assertIn('15:00',text)
        self.assertIn('ПРИЁМ ДНЯ',text)

    def test_generated_daily_tip_cached_with_source(self):
        result={'title':'Новый приём','body':'Уточняй действие перед съёмкой и найди хороший план.','mode':'text','source':'https://en.wikipedia.org/wiki/Shot_(filmmaking)'}
        with patch.object(server,'make_daily',return_value=result) as make:
            self.assertEqual(server.daily_content('tip',True),result)
            self.assertEqual(server.daily_content('tip',True),result)
        make.assert_called_once()

    def test_ai_searches_source_and_generates_new_tip(self):
        server.AI_KEY='testing-key'
        with patch.object(server,'creative_enabled',return_value=True), patch.object(server,'wiki_search',return_value={'title':'Camera angle','snippet':'A camera angle refers to the placement of a film camera in relation to the subject.','url':'https://en.wikipedia.org/wiki/Camera_angle'}) as lookup,patch.object(server,'ai_json',side_effect=[{'query':'camera angle cinematography'},{'title':'Выбери ракурс','body':'Ракурс камеры меняет точку зрения на героя. Выбери его прежде, чем нажать запись.'}]) as model:
            item=server.make_daily('tip')
        self.assertEqual(lookup.call_args.args[0],'camera angle cinematography')
        self.assertEqual(model.call_count,2)
        self.assertEqual(item['source'],'https://en.wikipedia.org/wiki/Camera_angle')
        server.AI_KEY=''

    def test_student_question_admin_reply(self):
        with patch.object(server,'send',return_value={'ok':True,'result':{'message_id':77}}) as sent:
            server.bot_message({'chat':{'type':'private'},'from':{'id':42},'text':'Как подготовиться к съёмке?'})
            self.assertIn('ВОПРОС #1',sent.call_args_list[0].args[1])
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'text':'Заряди камеру и проверь звук.','reply_to_message':{'message_id':77}})
        self.assertTrue(any(call.args[0]==42 and 'Заряди камеру' in call.args[1] for call in sent.call_args_list))
        with server.conn() as c:self.assertEqual(c.execute('select answered from questions where id=1').fetchone()['answered'],1)

    def test_question_in_group_is_forwarded(self):
        with patch.object(server,'send',return_value={'ok':True,'result':{'message_id':11}}) as sent:
            server.bot_message({'chat':{'type':'supergroup','id':-10042},'from':{'id':42},'text':'/ask@timecode_bot Можно снять интервью завтра?'})
        self.assertTrue(any(c.args[0]==11 and 'интервью завтра' in c.args[1] for c in sent.call_args_list))

    def test_admin_media_broadcast(self):
        with patch.object(server,'api',return_value={'ok':True}) as tg,patch.object(server,'send',return_value={'ok':True}):
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'caption':'/send Смотрите кадр','photo':[{'file_id':'small'},{'file_id':'large'}]})
        self.assertEqual(tg.call_args.args[0],'sendPhoto')
        self.assertEqual(tg.call_args.args[1]['photo'],'large')
        self.assertNotIn('/send',tg.call_args.args[1]['caption'])

    def test_admin_publish_button_and_ai_switch(self):
        with patch.object(server,'api',return_value={}),patch.object(server,'send',return_value={'ok':True}) as sent:
            server.callback({'id':'callback','from':{'id':11},'data':'admin:publish','message':{'chat':{'id':11}}})
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'text':'Завтра съёмка в студии'})
            self.assertTrue(any(c.args[0]=='-10042' and 'Завтра съёмка' in c.args[1] for c in sent.call_args_list))
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'text':'/ai off'})
        self.assertFalse(server.creative_enabled())
        with patch.object(server,'ai_json') as ai:
            self.assertEqual(server.make_daily('tip'),server.fallback_content('tip'))
        ai.assert_not_called()


if __name__ == '__main__':
    unittest.main()
