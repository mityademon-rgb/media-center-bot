import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from test_server import server
import editorial_voice,daily_status
class StatusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();server.DB=Path(self.tmp.name)/'bot.db';server.init()
  self.old_story=editorial_voice.story;self.old_out=server.Handler.out
  self.day='2026-10-09';self.s=vars(server).copy();self.s.update(today=lambda:self.day,digest=Mock());daily_status.install(self.s);self.s['init']()
  for uid in (1,2,3,4):server.roster(uid,'Автор '+str(uid))
 def tearDown(self):
  editorial_voice.story=self.old_story;server.Handler.out=self.old_out;self.tmp.cleanup()
 def participate(self,uid):
  with server.conn() as c:
   c.execute("insert into morning_checkins(user_id,day,mood,step) values(?,?,'Зомби','done')",(uid,self.day))
   c.execute('insert into truth_results values(?,?,1)',(self.day,uid))
 def test_ties_reward_everyone_and_settlement_is_stable(self):
  for uid in (1,2,3,4):self.participate(uid)
  text=self.s['status_settle']();self.assertEqual(text,self.s['status_settle']())
  for uid in (1,2,3,4):self.assertEqual(self.s['daily_status'](uid)['badge'],'microphone');self.assertIn('Автор '+str(uid),text)
  with server.conn() as c:self.assertEqual(c.execute('select count(*) from daily_status_history').fetchone()[0],4)
 def test_silent_day_replaces_trophy_privately(self):
  self.participate(1);self.s['status_settle']();self.day='2026-10-10';text=self.s['status_settle']()
  self.assertEqual(self.s['daily_status'](1)['badge'],'leaf');self.assertNotIn('Автор 1',text)
  with server.conn() as c:rows=c.execute("select chat from notification_outbox where message_key='status-pause:1'").fetchall()
  self.assertEqual([r['chat'] for r in rows],['1'])
 def test_one_action_does_not_win(self):
  with server.conn() as c:c.execute("insert into morning_checkins(user_id,day,mood,step) values(1,?,'Зомби','done')",(self.day,))
  self.s['status_settle']();self.assertIsNone(self.s['daily_status'](1))
