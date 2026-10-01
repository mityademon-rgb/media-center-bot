import datetime as dt
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import chat_games
import editorial_voice


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/'test.db'
        @contextmanager
        def conn():
            c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
            try:
                with c:yield c
            finally:c.close()
        self.conn=conn
        with conn() as c:
            c.executescript("create table users(id integer primary key,name text,enabled integer); create table notification_outbox(day text,message_key text,chat text,body text,keyboard text,delivered integer default 0,primary key(day,message_key,chat)); create table daily_content(day text,kind text,title text,body text,primary key(day,kind));")
            c.executemany('insert into users values(?,?,1)',[(42,'Матвей'),(-17,'Саша')])
        import html
        self.s={'conn':conn,'today':lambda:'2026-10-01','now':lambda:dt.datetime(2026,10,1,16,20),
                'esc':html.escape,'send':Mock(return_value={'ok':True}),'api':Mock(return_value={'ok':True}),
                'callback':Mock(),'bot_message':Mock(),'allowed':lambda uid:uid in (42,-17),'retry_notifications':Mock()}
        chat_games.install(self.s)

    def tearDown(self):self.temp.cleanup()

    def answer(self,uid,topic,step,choice):
        self.s['callback']({'id':'max' if uid<0 else 'tg-id','from':{'id':uid},'data':f'cg:a:20261001:{topic}:{step}:{choice}'})

    def test_both_messengers_finish_and_repeated_button_does_not_score_twice(self):
        for uid,topic in ((42,'f'),(-17,'i')):
            for step,q in enumerate(chat_games.GAMES[topic]['questions']):
                self.answer(uid,topic,step,q['correct'])
                self.answer(uid,topic,step,q['correct'])
            with self.conn() as c:row=c.execute('select * from chat_game_runs where user_id=?',(uid,)).fetchone()
            self.assertEqual((row['step'],row['score']),(5,5))
        texts=[call.args[1] for call in self.s['send'].call_args_list]
        self.assertTrue(any('Матвей, твой результат: 5/5' in t and 'Молодец' in t for t in texts))
        self.assertTrue(any('Саша, твой результат: 5/5' in t for t in texts))
        with self.conn() as c:posts=c.execute('select body from notification_outbox').fetchall()
        self.assertEqual(len(posts),4)
        self.assertTrue(all('Ответ:' in r['body'] for r in posts))

    def test_kimi_creates_and_caches_daily_questions(self):
        import copy
        questions=copy.deepcopy(chat_games.GAMES['f']['questions'])
        questions[0]['q']='Снимаешь друга у входа в студию: видны и он целиком, и само здание. Какой план у тебя получился?'
        self.s['AI_KEY']='test'
        self.s['ai_json']=Mock(side_effect=[{'questions':questions},{'ok':True}, {'questions':chat_games.GAMES['i']['questions']},{'ok':True}])
        self.s['chat_game_prepare']();self.s['chat_game_prepare']()
        self.assertEqual(self.s['ai_json'].call_count,4)
        with self.conn() as c:rows=c.execute('select source,body from chat_game_content').fetchall()
        self.assertEqual([r['source'] for r in rows],['kimi','kimi'])
        self.assertEqual(json.loads(rows[0]['body'])['questions'][0]['q'],questions[0]['q'])

    def test_invalid_kimi_questions_use_safe_backup(self):
        self.s['AI_KEY']='test';self.s['ai_json']=Mock(return_value={'questions':[{'q':'Broken'}]})
        self.s['chat_game_prepare']()
        with self.conn() as c:rows=c.execute('select source,body from chat_game_content').fetchall()
        self.assertTrue(all(r['source']=='backup' and len(json.loads(r['body'])['questions'])==5 for r in rows))

    def test_evening_story_includes_game_participants_even_without_checkin(self):
        self.answer(42,'f',0,0)
        self.s['AI_KEY']=''
        story=editorial_voice.story(self.s,[],False)
        self.assertIn('Матвей',story);self.assertIn('Все молодцы',story)
        self.assertNotIn('все ответили верно',story)

    def test_wrong_answers_get_specific_advice_and_resume_after_restart(self):
        self.answer(42,'f',0,1)
        # Reinstall against the same database, as a fresh process would.
        self.s['callback']=Mock();self.s['bot_message']=Mock();chat_games.install(self.s)
        for step,q in enumerate(chat_games.GAMES['f']['questions'][1:],1):self.answer(42,'f',step,(q['correct']+1)%3)
        text=self.s['send'].call_args.args[1]
        self.assertIn('0/5',text);self.assertIn('Есть к чему стремиться',text)
        self.assertIn('оставлять пространство перед взглядом',text)

    def test_invitation_queues_for_both_platforms_once_and_command_opens_menu(self):
        self.s['chat_game_invite']();self.s['chat_game_invite']()
        with self.conn() as c:rows=c.execute('select * from notification_outbox').fetchall()
        self.assertEqual(len(rows),2)
        for r in rows:
            buttons=json.loads(r['keyboard'])
            self.assertTrue(buttons[0][0]['callback_data'].startswith('cg:s:'))
        self.s['bot_message']({'from':{'id':42},'text':'/game'})
        self.assertEqual(len(self.s['send'].call_args.args[2]),2)

    def test_unreadable_photo_is_still_a_named_conversational_post(self):
        for comment in ('','Не могу рассмотреть изображение.','Кадр невозможно оценить.'):
            caption=editorial_voice.photo_caption('Матвей',comment,'2026-10-01')
            self.assertIn('Матвей',caption);self.assertIn('Рассмотрите снимок',caption)
            self.assertNotIn('не могу',caption.lower());self.assertNotIn('невозможно',caption.lower())

    def test_story_is_cached_and_uses_given_facts(self):
        rows=[{'name':'Матвей','mood':'Хороший','highlight':'Снял короткометражку','satisfied':'Да'}]
        body='Друзья, прочитал ваши ответы и улыбнулся. Матвей сегодня снял короткометражку. Это конкретный результат, и за него хочется похвалить. Мне интересно, что оказалось самым сложным на съёмке. Если хочешь рассказать, я на связи в этом чате. Сначала разберём твой опыт, а потом подумаем, что пригодится на следующей съёмке. Спасибо, что поделился историей своего дня. Хорошего вечера!'
        self.s['AI_KEY']='test';self.s['ai_json']=Mock(return_value={'text':body})
        self.assertEqual(editorial_voice.story(self.s,rows,False),body)
        self.assertEqual(editorial_voice.story(self.s,rows,False),body)
        self.assertEqual(self.s['ai_json'].call_count,2)
        request=self.s['ai_json'].call_args_list[0].args[1]
        self.assertIn('Снял короткометражку',request)


if __name__=='__main__':unittest.main()
