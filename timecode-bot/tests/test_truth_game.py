import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from test_server import server
import truth_game

class TruthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();server.DB=Path(self.tmp.name)/'bot.db';server.init();server.roster(42,'Саша');server.roster(-17,'Маша')
        self.s=vars(server).copy();self.s.update(today=lambda:'2026-10-10',AI_KEY='',allowed=lambda u:u in (42,-17),send=Mock(),api=Mock(),callback=Mock(),retry_notifications=Mock(),GROUP='')
        truth_game.install(self.s);self.s['init']()
    def tearDown(self):self.tmp.cleanup()
    def answer(self,day='2026-10-10'):
        self.s['callback']({'id':'max','from':{'id':42},'data':'tg:'+day+':1'})
    def test_result_is_private_card_public_score_and_idempotent(self):
        self.answer();self.answer()
        with server.conn() as c:
            self.assertEqual(c.execute('select count(*) from truth_results').fetchone()[0],1)
            cards=c.execute('select * from notification_photo_outbox').fetchall()
            self.assertEqual(len(cards),1);self.assertEqual(cards[0]['chat'],'42');self.assertTrue(cards[0]['photo'].startswith('truth-card:'))
            posts=c.execute('select body from notification_outbox').fetchall()
            self.assertEqual(len(posts),2)
            for post in posts:
                self.assertIn('Саша',post['body']);self.assertNotIn('Чубакки',post['body']);self.assertNotIn('Источник',post['body'])
    def test_stale_button_and_daily_cache(self):
        self.answer('2026-10-09')
        with server.conn() as c:self.assertEqual(c.execute('select count(*) from truth_results').fetchone()[0],0)
        first=self.s['truth_daily']();self.assertEqual(first,self.s['truth_daily']())
    def test_daily_invite_is_two_choices(self):
        self.s['chat_game_invite']()
        import json
        with server.conn() as c:rows=c.execute('select keyboard from notification_outbox').fetchall()
        self.assertEqual(len(json.loads(rows[0]['keyboard'])[0]),2)
