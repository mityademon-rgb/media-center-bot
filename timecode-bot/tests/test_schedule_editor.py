import sqlite3
import unittest
from unittest.mock import Mock
import schedule_editor


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
        self.c.executescript('create table lessons(id integer primary key,lab text,weekday int,start text,title text,place text,enabled int default 1);create table overrides(id integer primary key,day text,lab text,start text,title text,place text,cancelled int);')
        self.p={'kind':'lesson','action':'save','lab':'kids','weekday':1,'start':'18:00','title':'Съёмка','place':'Студия'}

    def tearDown(self):self.c.close()
    def act(self,p):return schedule_editor.act(self.c,p,'2026-10-08')

    def test_edit_delete_and_stale_guard(self):
        self.act(self.p);row=dict(self.c.execute('select * from lessons').fetchone())
        p={**self.p,'id':row['id'],'original':row,'start':'19:00'}
        self.act(p)
        with self.assertRaises(ValueError):self.act(p)
        current=dict(self.c.execute('select * from lessons').fetchone())
        self.act({'kind':'lesson','action':'remove','id':current['id'],'original':current})
        self.assertEqual(self.c.execute('select enabled from lessons').fetchone()[0],0)

    def test_date_replacement_deduplicates_and_can_be_removed(self):
        p={**self.p,'kind':'override','day':'2026-10-09','cancelled':True}
        self.act(p);self.act(p)
        row=dict(self.c.execute('select * from overrides').fetchone())
        self.assertEqual(self.c.execute('select count(*) from overrides').fetchone()[0],1)
        self.assertEqual(row['cancelled'],1)
        self.act({'kind':'override','action':'remove','id':row['id'],'original':row})
        self.assertEqual(self.c.execute('select count(*) from overrides').fetchone()[0],0)

    def test_invalid_input_rejected(self):
        for fields in ({'start':'25:00'},{'weekday':7},{'title':''},{'lab':'other'},{'place':'x'*81}):
            with self.assertRaises(ValueError):self.act({**self.p,**fields})
        with self.assertRaises(ValueError):self.act({**self.p,'kind':'override','day':'2026-10-07'})

    def test_endpoint_requires_teacher_and_valid_object(self):
        class Handler:
            do_POST=Mock()
            path='/api/schedule-edit'
            out=Mock()
            identity=Mock(return_value={'role':'member'})
            body=Mock(return_value=[])
        schedule_editor.install({'Handler':Handler})
        h=Handler();h.do_POST();self.assertEqual(h.out.call_args.args[1],403)
        h.identity.return_value={'role':'admin'};h.do_POST();self.assertEqual(h.out.call_args.args[1],400)
