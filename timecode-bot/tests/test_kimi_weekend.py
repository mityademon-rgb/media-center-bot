import datetime as dt
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch
import kimi_weekend as k
import shared_media


class ContestTests(unittest.TestCase):
    def setUp(self):
        self.thread_patch=patch.object(k.threading,'Thread');self.thread_patch.start()
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/'test.db'
        @contextmanager
        def conn():
            c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
            try:
                with c:yield c
            finally:c.close()
        self.conn=conn
        with conn() as c:
            c.executescript('create table users(id integer primary key,name text,role text,enabled integer,stage text); create table notification_outbox(day text,message_key text,chat text,body text,keyboard text,delivered integer default 0,unique(day,message_key,chat)); create table notification_photo_outbox(day text,period text,chat text,user_id integer,photo text,caption text,delivered integer default 0,unique(day,period,chat,user_id));')
            for uid in (1,2,3,4,5,-5,99):c.execute('insert into users values(?,?,?,1,?)',(uid,'Автор '+str(uid),'admin' if uid==99 else 'member',''))
        self.at=k.START;self.old_download=shared_media.download
        self.s={'conn':conn,'now':lambda:self.at,'today':lambda:self.at.date().isoformat(),'ADMINS':{99},'GROUP':'','AI_KEY':'','VISION_MODEL':'test','send':Mock(return_value={'ok':True}),'api':Mock(),'retry_notifications':Mock(),'bot_message':Mock(),'callback':Mock(),'class_reminders':Mock(),'esc':lambda x:x}
        self.old_callback=self.s['callback'];self.old_message=self.s['bot_message'];self.old_reminders=self.s['class_reminders']
        k.install(self.s)

    def tearDown(self):
        shared_media.download=self.old_download;self.tmp.cleanup();self.thread_patch.stop()

    def tap(self,uid,action):self.s['callback']({'id':'max','from':{'id':uid},'data':'kw:'+k.CAMPAIGN+':'+action})

    def send_photo(self,uid,photo):self.s['bot_message']({'from':{'id':uid},'chat':{'type':'private','id':uid},'photo':[{'file_id':photo}],'message_id':123,'caption':'Мой дубль'})

    def fill(self):
        self.at=k.CLOSE-dt.timedelta(seconds=1)
        for uid in (1,2,3,4):
            self.tap(uid,'task:0');self.send_photo(uid,'photo-'+str(uid))
        with self.conn() as c:c.execute("update kimi_frames set assessed=1,observation='На фотографии видна кружка в нижнем ракурсе',review='Ракурс поднял кружку до начальника. Ладно, переиграл.',fulfilment=8,creativity=7")

    def test_releases_are_durable_and_all_original_rubrics_survive(self):
        self.s['class_reminders']();self.s['kimi_weekend_tick']()
        with self.conn() as c:
            self.assertEqual(c.execute('select count(*) from kimi_events').fetchone()[0],1)
            self.assertEqual(c.execute('select count(*) from notification_photo_outbox').fetchone()[0],7)
        self.old_reminders.assert_called_once()
        self.at=dt.datetime.fromisoformat(TASK_TIME := k.TASKS[0][0]);self.s['kimi_weekend_tick']()
        self.at=k.CLOSE-dt.timedelta(seconds=1);self.s['kimi_weekend_tick']()
        with self.conn() as c:self.assertEqual(c.execute('select count(*) from kimi_events').fetchone()[0],4)
        self.s['callback']({'from':{'id':1},'data':'morning:start'})
        self.old_callback.assert_called_once()

    def test_photo_task_number_metadata_duplicates_and_status(self):
        self.at=k.CLOSE-dt.timedelta(seconds=1)
        for n in range(3):
            self.tap(-5,'task:'+str(n));self.send_photo(-5,'max:image:'+str(n))
        self.tap(-5,'task:2');self.send_photo(-5,'max:image:2')
        self.s['kimi_weekend_reviews']()
        with self.conn() as c:
            rows=c.execute('select * from kimi_frames').fetchall()
            self.assertEqual(len(rows),3);self.assertEqual({r['task'] for r in rows},{0,1,2})
            self.assertEqual(json.loads(rows[0]['metadata'])['platform'],'max')
        self.assertTrue(any('Режиссёр выходного дня' in str(call) for call in self.s['send'].call_args_list))
        self.at=k.CLOSE;self.tap(1,'task:0');self.send_photo(1,'late')
        with self.conn() as c:self.assertEqual(c.execute('select count(*) from kimi_frames').fetchone()[0],3)

    def test_admins_early_tasks_and_unselected_photos_are_ignored(self):
        self.tap(99,'task:0');self.tap(1,'task:0');self.send_photo(1,'early')
        with self.conn() as c:self.assertEqual(c.execute('select count(*) from kimi_frames').fetchone()[0],0)
        self.old_message.assert_called_once()

    def test_linked_accounts_share_one_changeable_vote(self):
        self.fill()
        self.s['bot_message']({'from':{'id':5},'chat':{'type':'private'},'text':'/kimi_link'})
        code=re_code(self.s['send'].call_args.args[1])
        self.s['bot_message']({'from':{'id':-5},'chat':{'type':'private'},'text':'/kimi_link '+code})
        self.at=k.VOTE;self.s['kimi_weekend_shortlist']()
        self.tap(5,'vote:1');self.tap(-5,'vote:2')
        with self.conn() as c:
            rows=c.execute('select * from kimi_votes').fetchall();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['slot'],2)
        self.at=k.FINAL;self.tap(5,'vote:3')
        with self.conn() as c:self.assertEqual(c.execute('select slot from kimi_votes').fetchone()[0],2)

    def test_persisted_final_separate_prizes_and_delivery_blocker(self):
        self.fill();self.at=k.VOTE;self.s['kimi_weekend_shortlist']();self.tap(5,'vote:2')
        self.at=k.FINAL;self.s['kimi_weekend_finish']()
        with self.conn() as c:
            self.assertEqual(c.execute('select count(*) from kimi_results').fetchone()[0],0)
            c.execute('update notification_photo_outbox set delivered=1')
        self.s['kimi_weekend_finish']();self.s['kimi_weekend_finish']()
        with self.conn() as c:
            rows=c.execute('select * from kimi_results').fetchall();self.assertEqual(len(rows),1)
            self.assertNotEqual(rows[0]['magnet'],rows[0]['keyring'])
            self.assertEqual(rows[0]['magnet'],2)

    def test_unseen_frames_do_not_get_fake_reviews_or_shortlist(self):
        self.fill()
        with self.conn() as c:c.execute('update kimi_frames set assessed=0 where user_id=1')
        self.at=k.VOTE;self.assertFalse(self.s['kimi_weekend_shortlist']())
        with self.conn() as c:self.assertEqual(c.execute('select count(*) from kimi_shortlist').fetchone()[0],0)

    def test_vision_receives_actual_bytes_and_persists_observation(self):
        self.fill()
        with self.conn() as c:c.execute('update kimi_frames set assessed=0 where user_id=1')
        self.s['AI_KEY']='configured'
        response={'visible':True,'observation':'В кадре кружка снята снизу на тёмном фоне','review':'Кружку сделал начальником. Ладно, этот ракурс забираю.','fulfilment':9,'creativity':8}
        self.s['kimi_request']=Mock(return_value={'choices':[{'message':{'content':json.dumps(response)}}]})
        with patch.object(shared_media,'download',return_value=b'\xff\xd8actual-image'):
            self.s['kimi_weekend_reviews']()
        data=self.s['kimi_request'].call_args.args[1]
        self.assertIn('data:image/jpeg;base64,',data['messages'][0]['content'][1]['image_url']['url'])
        self.assertIn(k.TASKS[0][2],data['messages'][0]['content'][0]['text'])
        with self.conn() as c:
            row=c.execute('select * from kimi_frames where user_id=1').fetchone()
            self.assertEqual(row['fulfilment'],9);self.assertEqual(row['review_delivered'],1)


def re_code(body):return body.split('/kimi_link ')[1].split('.')[0]
if __name__=='__main__':unittest.main()
