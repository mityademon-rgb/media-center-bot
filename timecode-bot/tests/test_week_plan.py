import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from test_server import server
import week_plan

class WeekTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();server.DB=Path(self.temp.name)/'week.db';server.ADMINS={11};server.init()
        for uid,name in ((11,'Дмитрий'),(42,'Матвей'),(-17,'Саша')):server.roster(uid,name)
        self.at=dt.datetime.fromisoformat('2026-10-05T07:30:00+03:00')
        self.s=vars(server).copy();self.s.update(now=lambda:self.at,today=lambda:self.at.date().isoformat(),GROUP='',AI_KEY='',send=Mock(return_value={'ok':True}),api=Mock(return_value={'ok':True}),retry_notifications=Mock(),morning=Mock(),class_reminders=Mock(),bot_message=Mock(),callback=Mock(),allowed=lambda uid:uid in (11,42,-17),chat_game_for=Mock())
        week_plan.install(self.s)
        with server.conn() as c:c.execute('create table if not exists chat_game_runs(user_id integer,day text,topic text,step integer,score integer,primary key(user_id,day,topic))')
    def tearDown(self):self.temp.cleanup()
    def test_dialogue_keeps_context_private_between_students(self):
        with patch.object(server,'AI_KEY','test'),patch.object(server,'ai_json',return_value={'text':'Попробуй поставить телефон ближе. Тогда голос станет слышнее. Что сейчас шумит рядом?'}) as ai:
            server.chat_reply('У меня плохо слышно интервью',42)
            server.chat_reply('А если рядом дорога?',42)
            second=json.loads(ai.call_args.args[1])
            self.assertIn('У меня плохо слышно интервью',str(second['dialogue']))
            server.chat_reply('Как выбрать ракурс?',-17)
            third=json.loads(ai.call_args.args[1])
            self.assertEqual(third['dialogue'],[])

    def test_morning_rule_and_daily_game_only(self):
        self.s['morning']();self.s['morning']()
        with server.conn() as c:
            posts=c.execute('select body,keyboard from notification_outbox').fetchall()
            self.assertEqual(len(posts),3);self.assertIn('25 из 25',posts[0]['body']);self.assertIn('все, кто справится',posts[0]['body'])
        self.assertTrue(self.s['weekly_game_menu'](42))
        self.assertEqual(len(self.s['send'].call_args.args[2]),1)
        self.assertFalse(self.s['weekly_game_allowed'](42,'20261005','i'))
        self.at+=dt.timedelta(days=1);self.assertFalse(self.s['weekly_game_allowed'](42,'20261005','f'))
    def test_prize_all_qualified_excludes_wrong_score_and_admin(self):
        with server.conn() as c:
            for uid in (11,42,-17):
                for d,(topic,*_) in week_plan.DAYS.items():c.execute('insert into chat_game_runs values(?,?,?,?,?)',(uid,d,topic,5,4 if uid==-17 and d=='20261009' else 5))
        self.at=dt.datetime.fromisoformat('2026-10-10T09:00:00+03:00');self.s['week_plan_tick']();self.s['week_plan_tick']()
        with server.conn() as c:
            r=c.execute('select * from week_rewards').fetchone();self.assertEqual([u['id'] for u in json.loads(r['eligible'])],[42]);self.assertEqual(c.execute('select count(*) from notification_outbox').fetchone()[0],4)
    def test_wednesday_three_clear_steps_and_private_answers(self):
        self.at=dt.datetime.fromisoformat('2026-10-07T10:00:00+03:00')
        self.s['week_plan_tick']();self.s['callback']({'id':'max','from':{'id':-17},'data':'adq:start'})
        for msg in ({'photo':[{'file_id':'max:image:one'}],'max_photo':{'url':'https://i.oneme.ru/a'}},{'text':'Хранит секреты второго носка'},{'text':'Один зато независимый'}):
            self.s['bot_message']({'chat':{'type':'private'},'from':{'id':-17},**msg})
        with server.conn() as c:
            r=c.execute('select * from ad_quest').fetchone();self.assertEqual((r['done'],r['step']),(1,3))
            posts=[r['body'] for r in c.execute('select body from notification_outbox')]
            self.assertTrue(any('Саша прошёл квест' in p and '3/3' in p for p in posts))
            self.assertFalse(any('Хранит секреты' in p for p in posts))
    def test_quest_closes_and_other_callbacks_preserve_partial(self):
        self.at=dt.datetime.fromisoformat('2026-10-07T10:00:00+03:00');self.s['callback']({'id':'max','from':{'id':42},'data':'adq:start'})
        self.s['bot_message']({'chat':{'type':'private'},'from':{'id':42},'photo':[{'file_id':'photo'}]})
        self.s['callback']({'id':'max','from':{'id':42},'data':'evening:day:Хороший'})
        with server.conn() as c:self.assertEqual(tuple(c.execute('select active,step from ad_quest').fetchone()),(0,1))
        self.at=self.at.replace(hour=20);self.s['callback']({'id':'max','from':{'id':42},'data':'adq:start'})
        with server.conn() as c:self.assertEqual(c.execute('select done from ad_quest').fetchone()[0],0)

if __name__=='__main__':unittest.main()
