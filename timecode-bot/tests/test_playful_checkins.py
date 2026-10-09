import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from test_server import server
import playful_checkins


class PlayfulTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();server.DB=Path(self.temp.name)/'bot.db';server.ADMINS={11}
        server.init();server.roster(42,'Саша');server.roster(-17,'Маша')
        self.s=vars(server).copy();self.old=Mock();self.clock=dt.datetime(2026,10,10,9,15)
        self.s.update(bot_message=self.old,callback=Mock(),send=Mock(return_value={'ok':True}),api=Mock(),
                      allowed=lambda uid:uid in (42,-17,11),today=lambda:'2026-10-10',now=lambda:self.clock,
                      checkin_open=lambda period:period==('am' if self.clock.hour<12 else 'pm'),photo_comment=Mock(return_value='Боковой свет выделил край чашки.'),GROUP='')
        playful_checkins.install(self.s);self.s['init']()

    def tearDown(self):self.temp.cleanup()
    def click(self,period,index,uid=42,day='2026-10-10'):
        self.s['callback']({'id':'max','from':{'id':uid},'data':f'pc:{period}:{index}:{day}'})
    def photo(self,uid=42):
        self.s['bot_message']({'chat':{'type':'private'},'from':{'id':uid},'photo':[{'file_id':'photo-42'}]})

    def test_one_tap_finishes_without_question_chain_and_keeps_photo(self):
        self.click('am',0);self.photo();self.click('am',1)
        with server.conn() as c:r=c.execute('select * from morning_checkins where user_id=42').fetchone()
        self.assertEqual(r['step'],'done');self.assertEqual(r['photo'],'photo-42');self.assertIn('100%',r['mood'])
        self.assertEqual(r['visible'],1)

    def test_photo_without_status_included_and_comment_recorded(self):
        self.photo(-17)
        with server.conn() as c:
            row=c.execute('select * from morning_checkins where user_id=-17').fetchone()
            meta=c.execute('select * from photo_hunts where user_id=-17').fetchone()
        self.assertEqual(row['mood'],'Фотоохота');self.assertEqual(row['step'],'done')
        self.assertEqual(meta['comment'],'Боковой свет выделил край чашки.')

    def test_evening_states_and_no_forced_text(self):
        self.clock=dt.datetime(2026,10,10,18,30);self.click('pm',2)
        self.s['bot_message']({'chat':{'type':'private'},'from':{'id':42},'text':'Что ты умеешь?'})
        self.old.assert_called_once()
        with server.conn() as c:r=c.execute('select * from evening_checkins where user_id=42').fetchone()
        self.assertEqual(r['step'],'done');self.assertIn('1%',r['mood'])

    def test_old_day_does_not_modify_today(self):
        self.click('am',0,day='2026-10-09')
        with server.conn() as c:self.assertEqual(c.execute('select count(*) from morning_checkins').fetchone()[0],0)

    def test_invitation_has_four_buttons_and_concrete_hunt(self):
        self.s['morning']();calls=self.s['send'].call_args_list
        self.assertEqual(len(calls),2)
        for call in calls:
            text,keyboard=call.args[1:]
            self.assertIn('Фотоохота',text);self.assertEqual(len(keyboard),4)
            self.assertNotIn('Выспался',text)
