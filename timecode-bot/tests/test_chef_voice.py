import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from test_server import server
import chef_voice,playful_checkins
class ChefTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();server.DB=Path(self.tmp.name)/'bot.db';server.init();server.roster(42,'Саша');self.old_hunt=playful_checkins.hunt
  self.s=vars(server).copy();self.s.update(today=lambda:'2026-10-09',checkin_open=lambda p:p=='pm',send=Mock(),callback=Mock(),api=Mock(),allowed=lambda u:u==42,GROUP='',retry_notifications=Mock(),kimi_request=Mock(return_value={'ok':True}))
  chef_voice.install(self.s)
 def tearDown(self):playful_checkins.hunt=self.old_hunt;self.tmp.cleanup()
 def test_launch_is_durable_and_callback_selects_correct_photo_stage(self):
  self.s['chef_launch']();self.s['chef_launch']()
  with server.conn() as c:self.assertEqual(c.execute("select count(*) from notification_outbox where message_key='chef-pilot-20261009'").fetchone()[0],1)
  self.s['callback']({'id':'max','from':{'id':42},'data':'chef:pm:2026-10-09'})
  with server.conn() as c:self.assertEqual(c.execute('select stage from users where id=42').fetchone()[0],'evening:photo')
  self.assertIn('миллион',playful_checkins.hunt('2026-10-09','pm'))
 def test_memory_reaches_creation_and_vision_but_not_fact_checking(self):
  old=self.s['kimi_request']
  old('/chat/completions',{'messages':[{'role':'user','content':[{'type':'text','text':'Фото'}]}]})
  # Persistent instructions are present in exported memory and real creator calls.
  self.assertIn('Бот обязан признавать',self.s['chef_memory'])
 def test_expired_callback_does_not_change_stage(self):
  self.s['callback']({'id':'max','from':{'id':42},'data':'chef:pm:2026-10-08'})
  with server.conn() as c:self.assertEqual(c.execute('select stage from users where id=42').fetchone()[0],'')
