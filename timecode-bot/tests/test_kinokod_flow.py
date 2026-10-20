"""Regression checks for KinoKod's two-step narrative (no child messages)."""
import datetime as dt
import html
import importlib.util
import pathlib
import sqlite3
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('kinokod', ROOT/'kinokod.py')
kinokod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kinokod)

class KinoKodStoryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        create table users(id integer primary key,name text,role text,enabled integer);
        insert into users values(101,'Tester','member',1);
        create table notification_outbox(day text,message_key text,chat text,body text,keyboard text,delivered integer default 0,
          unique(day,message_key,chat));
        create table notification_unreachable(chat text primary key,reason text,created integer);
        """)
        self.messages=[]
        self.when=dt.datetime.fromisoformat('2026-10-20T14:05:00+03:00')
        def send(uid,body,keyboard=None):
            self.messages.append((uid,body,keyboard))
            return {'ok':True}
        self.s={'bot_message':lambda msg:None,'callback':lambda q:None,
                'class_reminders':lambda:None,'conn':lambda:self.db,
                'now':lambda:self.when,'today':lambda:self.when.date().isoformat(),
                'send':send,'esc':lambda x:html.escape(str(x),quote=False),
                'api':lambda endpoint,payload:{'ok':True},
                'retry_notifications':lambda key=None:None,
                'ADMINS':[]}
        kinokod.install(self.s)
    def cb(self,data):
        self.s['callback']({'id':'max','from':{'id':101},'data':data})
    def test_immediate_clue_followup_and_closure(self):
        self.cb('kc:0:2')
        self.assertTrue(any('запись' in msg[1].lower() and 'Журнал' not in msg[1] for msg in self.messages))
        self.assertEqual(len(self.messages[-1][2]),3)
        self.cb('kc:0:next:1')
        self.assertIn('18:30',self.messages[-1][1])
        self.assertIn('проход',self.messages[-1][1])
        row=self.db.execute('select action from kinokod_steps where user_id=101 and slot=0').fetchone()
        self.assertEqual(row['action'],1)
    def test_old_buttons_do_not_change_answers(self):
        self.cb('kc:0:0')
        self.cb('kc:0:2')
        self.assertEqual(self.db.execute('select choice from kinokod_votes where user_id=101 and slot=0').fetchone()['choice'],0)
        self.cb('kc:0:next:2')
        previous=len(self.messages)
        self.cb('kc:0:next:0')
        self.assertIn('уже пройден',self.messages[-1][1])
        self.assertEqual(len(self.messages),previous+1)
        self.assertEqual(self.db.execute('select count(*) from kinokod_steps').fetchone()[0],1)
    def test_existing_participant_gets_missing_followup(self):
        self.db.execute('insert into kinokod_players(user_id,joined_at) values(101,0)')
        self.db.execute('insert into kinokod_votes(user_id,slot,choice,updated) values(101,0,1,0)')
        self.s['kinokod_tick']()
        messages=self.db.execute("select message_key,body,keyboard from notification_outbox where message_key like 'kc-bridge-%'").fetchall()
        self.assertEqual(len(messages),1)
        self.assertIn('футляр',messages[0]['body'].lower())
        self.assertIn('kc:0:next:',messages[0]['keyboard'])
        self.cb('kc:0:next:0')
        status=self.db.execute('select delivered from notification_outbox where message_key=?',(messages[0]['message_key'],)).fetchone()['delivered']
        self.assertEqual(status,-2)
    def test_photo_skip_completes_even_after_photo_prompt(self):
        self.when=dt.datetime.fromisoformat('2026-10-20T18:40:00+03:00')
        self.cb('kc:1:photo')
        self.cb('kc:1:skip')
        self.assertTrue(any('09:00' in m[1] for m in self.messages))
        self.assertEqual(self.db.execute('select caption from kinokod_votes where user_id=101 and slot=1').fetchone()['caption'],'SKIPPED')
    def test_future_slots_locked(self):
        self.cb('kc:2:0')
        self.assertIsNone(self.db.execute('select choice from kinokod_votes where slot=2').fetchone())

if __name__=='__main__':
    unittest.main()
