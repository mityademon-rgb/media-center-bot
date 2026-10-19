import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shared_media
import teacher_mode


class TeacherModeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / 'test.sqlite')
        self.sent = []
        self.old_photo = shared_media.send_photo
        with self.conn() as c:
            c.executescript('''create table users(id integer primary key, name text, role text, stage text, lab text, enabled integer);
            create table notification_outbox(day text, message_key text, chat text, body text, keyboard text, delivered integer);
            create table notification_photo_outbox(day text, period text, chat text, user_id integer, photo text, caption text, delivered integer);''')
            c.execute("insert into users values(10,'Ученик','member','','kids',1)")

        def roster(uid, name):
            with self.conn() as c:c.execute('insert or ignore into users values(?,?,?,?,?,1)',(uid,name,'member','','kids'))
        def message(msg):self.sent.append(('original', msg))
        def send(chat, body, keyboard=None):
            self.sent.append((chat,body,keyboard));return {'ok':True}
        class Handler:
            path = '/api/state'
            user = None
            def identity(self):return self.user
            def body(self, max_size=100000):return self.payload
            def out(self, data, status=200):return data,status
            def do_POST(self):return 'original post'
        self.Handler=Handler
        self.ns={'conn':self.conn,'roster':roster,'bot_message':message,'callback':lambda q:self.sent.append(('callback',q)),
                 'scheduler':lambda:None,'send':send,'api':lambda method,data=None:{'ok':True},
                 'retry_notifications':lambda:None,'allowed':lambda uid:self.row(uid) is not None,
                 'ADMINS':set(),'BASE':'https://example.test/tc/','Handler':Handler}
        teacher_mode.install(self.ns)

    def tearDown(self):
        shared_media.send_photo=self.old_photo
        self.directory.cleanup()

    @contextlib.contextmanager
    def conn(self):
        c=sqlite3.connect(self.db)
        c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()

    def row(self, uid):
        with self.conn() as c:return c.execute('select * from users where id=?',(uid,)).fetchone()

    def msg(self, uid, text='/start'):
        self.ns['bot_message']({'chat':{'type':'private','id':uid},'from':{'id':uid,'first_name':'Аня'},'text':text})

    def test_teacher_registration_defaults_to_lessons_only_and_can_toggle(self):
        self.msg(21)
        self.assertEqual(self.row(21)['stage'],'onboard:attendance')
        self.assertIn('Ты занимаешься',self.sent[-1][1])
        self.ns['callback']({'id':'max','from':{'id':21},'data':'onboard:attendance:no'})
        self.assertEqual(self.row(21)['role'],'teacher')
        self.assertEqual(self.row(21)['stage'],'onboard:teacher_daily')
        self.msg(21,'Нет')
        self.assertFalse(self.ns['teacher_daily_enabled'](21))
        self.assertEqual(self.row(21)['stage'],'')
        self.msg(21,'/daily on')
        self.assertTrue(self.ns['teacher_daily_enabled'](21))
        self.ns['callback']({'id':'max','from':{'id':21},'data':'teacher:daily:off'})
        self.assertFalse(self.ns['teacher_daily_enabled'](21))

    def test_student_branch_and_existing_member_remain_students(self):
        self.msg(22)
        self.msg(22,'Да')
        self.assertEqual(self.row(22)['stage'],'onboard:lab')
        self.ns['callback']({'id':'max','from':{'id':22},'data':'onboard:lab:media'})
        self.assertEqual(self.row(22)['lab'],'media')
        self.assertEqual(self.row(22)['stage'],'')
        self.msg(10)
        self.assertEqual(self.sent[-1][0],'original')
        self.ns['callback']({'id':'max','from':{'id':10},'data':'onboard:lab:kids'})
        self.assertEqual(self.sent[-1][0],'callback')

    def test_opt_out_suppresses_queued_text_photo_and_scheduled_direct_messages(self):
        self.msg(23)
        self.msg(23,'Нет')
        self.msg(23,'Нет')
        with self.conn() as c:
            c.execute("insert into notification_outbox values('2026-10-20','tip','23','x','null',0)")
            c.execute("insert into notification_photo_outbox values('2026-10-20','pm','23',10,'photo','caption',0)")
        self.ns['retry_notifications']()
        with self.conn() as c:
            self.assertEqual(c.execute('select delivered from notification_outbox').fetchone()[0],-2)
            self.assertEqual(c.execute('select delivered from notification_photo_outbox').fetchone()[0],-2)
        self.assertTrue(shared_media.send_photo(self.ns,23,'photo','caption')['suppressed'])
        before=len(self.sent)
        teacher_mode._scheduled.active=True
        try:self.ns['send'](23,'morning')
        finally:teacher_mode._scheduled.active=False
        self.assertEqual(len(self.sent),before)

    def test_state_and_post_gate_follow_mode(self):
        self.msg(24);self.msg(24,'Нет');self.msg(24,'Нет')
        h=self.Handler();h.user=self.row(24)
        state={'me':{'id':24,'role':'teacher'},'quests':[1],'lessons':[2],'changes':[], 'latest':[], 'tip':[1], 'mission':[2]}
        data,status=h.out(state)
        self.assertEqual(status,200)
        self.assertFalse(data['me']['daily_enabled'])
        self.assertEqual(data['lessons'],[])
        h.path='/api/game';self.assertEqual(h.do_POST()[1],403)
        h.path='/api/teacher-mode';h.payload={'enabled':True}
        self.assertEqual(h.do_POST()[1],200)
        self.assertEqual(h.do_POST()[0]['daily_enabled'],True)
        h.path='/api/game';self.assertEqual(h.do_POST(),'original post')


if __name__=='__main__':unittest.main()
