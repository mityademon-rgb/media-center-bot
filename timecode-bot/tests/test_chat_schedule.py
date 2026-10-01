import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from test_server import server
import chat_schedule


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();server.DB=Path(self.temp.name)/'bot.db'
        server.ADMINS={11};server.init();server.roster(11,'Преподаватель');server.roster(42,'Ученик');server.roster(-17,'MAX')
        self.s=vars(server).copy()
        self.s.update(send=Mock(return_value={'ok':True}),api=Mock(return_value={'ok':True}),retry_notifications=Mock(),
                      callback=Mock(),bot_message=Mock(),GROUP='',BASE='https://timecode-lab.ru/tc',today=lambda:'2026-10-01',now=lambda:dt.datetime(2026,10,1))
        chat_schedule.install(self.s)

    def tearDown(self):self.temp.cleanup()

    def click(self,data,uid=11):self.s['callback']({'id':'max','from':{'id':uid},'data':data})
    def type(self,text):self.s['bot_message']({'chat':{'type':'private','id':11},'from':{'id':11},'text':text})

    def test_add_requires_save_and_notifies_every_platform_once(self):
        self.click('sch:action:add');self.click('sch:lab:kids');self.click('sch:weekday:1')
        self.type('18:00');self.type('Интервью');self.type('Студия')
        with server.conn() as c:self.assertEqual(c.execute('select count(*) from notification_outbox').fetchone()[0],0)
        self.click('sch:commit');self.click('sch:commit')
        with server.conn() as c:
            lessons=c.execute("select * from lessons where title='Интервью'").fetchall()
            notices=c.execute('select * from notification_outbox').fetchall()
        self.assertEqual(len(lessons),1);self.assertEqual(lessons[0]['start'],'18:00')
        self.assertEqual(len(notices),3);self.assertEqual({r['chat'] for r in notices},{'11','42','-17'})
        self.assertTrue(all('Загляни в расписание!!!' in r['body'] for r in notices))

    def test_edit_weekly_lesson_keeps_same_id(self):
        with server.conn() as c:
            lesson_id=c.execute("insert into lessons(lab,weekday,start,title,place) values('kids',1,'18:00','Старое','Студия')").lastrowid
        self.click('sch:action:edit');self.click('sch:lab:kids');self.click('sch:lesson:'+str(lesson_id));self.click('sch:weekday:3')
        self.type('19:00');self.type('Новое');self.type('Кабинет 2');self.click('sch:commit')
        with server.conn() as c:r=c.execute('select * from lessons where id=?',(lesson_id,)).fetchone()
        self.assertEqual((r['weekday'],r['start'],r['title']),(3,'19:00','Новое'))

    def test_date_cancellation_and_unauthorized_buttons(self):
        self.click('sch:action:cancel',42);self.s['send'].assert_not_called()
        self.click('sch:action:cancel');self.click('sch:lab:media');self.type('05.10.2026');self.click('sch:commit')
        with server.conn() as c:r=c.execute('select * from overrides').fetchone()
        self.assertEqual((r['day'],r['lab'],r['cancelled']),('2026-10-05','media',1))


if __name__=='__main__':unittest.main()
