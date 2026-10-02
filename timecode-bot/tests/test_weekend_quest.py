import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from test_server import server
import weekend_quest as wq


class WeekendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        server.DB=Path(self.temp.name)/'quest.db';server.ADMINS={11};server.init()
        for uid,name in ((11,'Дмитрий'),(42,'Матвей'),(-17,'Саша')):server.roster(uid,name)
        self.at=dt.datetime.fromisoformat('2026-10-02T18:30:00+03:00')
        self.s=vars(server).copy()
        self.s.update(now=lambda:self.at,today=lambda:self.at.date().isoformat(),GROUP='',AI_KEY='',send=Mock(return_value={'ok':True}),api=Mock(return_value={'ok':True}),retry_notifications=Mock(),bot_message=Mock(),callback=Mock(),class_reminders=Mock(),allowed=lambda uid:uid in (11,42,-17))
        self.old_callback=self.s['callback'];self.old_message=self.s['bot_message']
        wq.install(self.s)

    def tearDown(self):self.temp.cleanup()

    def tap(self,uid,action):
        self.s['callback']({'id':'max' if uid<0 else 'telegram','from':{'id':uid},'data':'wq:'+wq.CAMPAIGN+':'+action})

    def message(self,uid,body='',photo=''):
        self.s['bot_message']({'chat':{'type':'private','id':uid},'from':{'id':uid},'text':body,'photo':[{'file_id':photo}] if photo else []})

    def fill(self,uid):
        self.at=dt.datetime.fromisoformat('2026-10-04T16:10:00+03:00')
        for n,task in enumerate(wq.TASKS):
            self.tap(uid,'task:'+str(n))
            if n==1:
                self.tap(uid,'answer:1:0')
                self.tap(uid,'answer:1:2')
            else:
                for i in range(task['photos']):self.message(uid,photo=f'photo-{uid}-{n}-{i}')
                if task['text']:self.message(uid,'Чайник потерял выходной. Он искал его под столом. Нашёл в воскресенье и остыл.')

    def test_prize_draw_cannot_happen_before_result_time(self):
        self.s['weekend_quest_finish']()
        with server.conn() as c:
            wq.tables(c)
            self.assertEqual(c.execute('select count(*) from weekend_draws').fetchone()[0],0)

    def test_release_times_and_no_duplicate_next_day(self):
        self.s['weekend_quest_announce']();self.s['weekend_quest_announce']()
        self.at=dt.datetime.fromisoformat('2026-10-03T10:00:00+03:00')
        self.s['weekend_quest_tick']();self.s['weekend_quest_tick']()
        with server.conn() as c:self.assertEqual(c.execute('select count(*) from notification_outbox').fetchone()[0],6)
        self.at=dt.datetime.fromisoformat('2026-10-04T10:00:00+03:00');self.s['weekend_quest_tick']()
        with server.conn() as c:self.assertEqual(c.execute('select count(*) from notification_outbox').fetchone()[0],15)
        self.tap(42,'task:5')
        with server.conn() as c:self.assertIsNone(c.execute('select * from weekend_answers where task=5').fetchone())

    def test_complete_both_platforms_and_one_persisted_winner(self):
        for uid in (42,-17):self.fill(uid)
        self.at=wq.RESULT
        with patch.object(wq.secrets,'choice',side_effect=lambda rows:rows[-1]) as draw:
            self.s['weekend_quest_finish']();self.s['weekend_quest_finish']()
            self.at+=dt.timedelta(days=1);self.s['weekend_quest_finish']()
        self.assertEqual(draw.call_count,1)
        with server.conn() as c:
            result=c.execute('select * from weekend_draws').fetchone()
            self.assertEqual(set(json.loads(result['eligible'])),{42,-17})
            self.assertIn(result['winner'],(42,-17))
            self.assertEqual(c.execute('select count(*) from notification_photo_outbox').fetchone()[0],6)
            self.assertEqual(c.execute('select count(distinct body) from notification_outbox').fetchone()[0],1)
        self.assertIn('Дмитрий Витальевич',result['body'])

    def test_incomplete_and_admin_excluded_and_deadline_enforced(self):
        self.at=dt.datetime.fromisoformat('2026-10-04T16:10:00+03:00');self.tap(42,'task:0');self.message(42,'Чайник',photo='photo')
        self.tap(11,'task:0')
        self.at=wq.CLOSE;self.tap(42,'task:5');self.message(42,'Эта история уже после закрытия.')
        self.at=wq.RESULT;self.s['weekend_quest_finish']()
        with server.conn() as c:
            result=c.execute('select * from weekend_draws').fetchone()
            self.assertEqual(json.loads(result['eligible']),[]);self.assertIsNone(result['winner'])
            self.assertEqual(c.execute('select count(*) from weekend_answers where done=1').fetchone()[0],1)
            self.assertEqual(c.execute('select count(*) from weekend_players where user_id=11').fetchone()[0],0)

    def test_album_duplicate_does_not_complete_three_distinct_photos(self):
        self.at=dt.datetime.fromisoformat('2026-10-03T18:01:00+03:00');self.tap(42,'task:2')
        self.message(42,photo='same');self.message(42,photo='same');self.message(42,photo='other')
        with server.conn() as c:
            row=c.execute('select * from weekend_answers').fetchone();self.assertEqual(row['done'],0);self.assertEqual(len(json.loads(row['photos'])),2)
        self.message(42,photo='third')
        with server.conn() as c:self.assertEqual(c.execute('select done from weekend_answers').fetchone()[0],1)

    def test_poll_callback_suspends_quest_and_preserves_partial_answer(self):
        self.at=wq.START;self.tap(42,'task:0');self.message(42,photo='one')
        self.s['callback']({'from':{'id':42},'data':'evening:day:Хороший'})
        self.old_callback.assert_called_once()
        self.message(42,'Мой день прошёл хорошо')
        self.old_message.assert_called_once()
        self.tap(42,'task:0');self.message(42,'Чайник')
        with server.conn() as c:self.assertEqual(c.execute('select done from weekend_answers').fetchone()[0],1)


if __name__=='__main__':unittest.main()
