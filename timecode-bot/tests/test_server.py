import hashlib
import hmac
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'server.py'
spec = importlib.util.spec_from_file_location('timecode_server', MODULE)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class BotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        server.DB = Path(self.temp.name) / 'bot.db'
        server.SECRET = 'a'*40
        server.TOKEN = '123:TEST'
        server.JOIN = 'secret-join-test-1234567890'
        server.ADMINS = {11}
        server.GROUP = '-10042'
        server.init()
        server.roster(11, 'Дмитрий')
        server.roster(42, 'Матвей')

    def tearDown(self):
        self.temp.cleanup()

    def test_database_connection_closes_after_context(self):
        with server.conn() as c:
            self.assertEqual(c.execute('select count(*) from users').fetchone()[0],2)
        with self.assertRaises(__import__('sqlite3').ProgrammingError):
            c.execute('select 1')

    def test_daily_photo_collected_until_evening_report(self):
        with server.conn() as c:
            c.execute('insert into daily_photos(user_id,day,photo,created) values(?,?,?,?)',(42,server.today(),'photo-test',1))
        with patch.object(server,'send_attachment',return_value={'ok':True}) as delivery:
            server.publish_daily_photo(42,server.today())
        delivery.assert_not_called()
        with server.conn() as c:row=c.execute('select status from daily_photos').fetchone()
        self.assertEqual(row['status'],'collected')

    def test_admin_menu_has_persistent_write_to_all_button(self):
        with patch.object(server,'api',return_value={'ok':True}) as api,patch.object(server,'send',return_value={'ok':True}):
            result=server.admin_menu(11)
        payload=api.call_args.args[1]
        self.assertTrue(payload['reply_markup']['is_persistent'])
        self.assertFalse(payload['reply_markup']['one_time_keyboard'])
        self.assertEqual(payload['reply_markup']['keyboard'][0][0]['text'],'📣 Написать всем')
        self.assertTrue(result['ok'])

    def test_evening_digest_retries_failed_delivery_without_duplicate(self):
        scope=vars(server).copy()
        scope['GROUP']=''
        scope['AI_KEY']=''
        attempts=[]
        ready=[False]
        def deliver(chat,message,keyboard=None):
            attempts.append(chat)
            return {'ok':ready[0]}
        scope['send']=deliver
        scope['api']=lambda *args:{'ok':True}
        server.notification_delivery.install(scope)
        scope['digest']('pm')
        with server.conn() as c:
            row=c.execute('select delivered from notification_outbox where chat=?',(str(42),)).fetchone()
        self.assertEqual(row['delivered'],0)
        ready[0]=True
        scope['retry_notifications']()
        with server.conn() as c:
            self.assertEqual(c.execute('select delivered from notification_outbox where chat=?',(str(42),)).fetchone()['delivered'],1)
        before=len(attempts)
        scope['retry_notifications']()
        self.assertEqual(len(attempts),before)

    def test_checkin_photos_reach_both_messengers(self):
        server.roster(-17,'MAX student')
        with server.conn() as c:
            c.execute("insert into evening_checkins(user_id,day,mood,photo,step) values (?,?,?,?,?)",(42,server.today(),'Хороший','telegram-photo','done'))
            c.execute("insert into evening_checkins(user_id,day,mood,photo,step) values (?,?,?,?,?)",(-17,server.today(),'Хороший','max:image:max-token','done'))
            c.execute("insert into daily_photos(user_id,day,photo,created) values(?,?,?,?)",(42,server.today(),'second-photo',1))
        scope=vars(server).copy();scope['GROUP']='';scope['AI_KEY']='';scope['MAX_TOKEN']='test'
        scope['send']=lambda *args,**kwargs:{'ok':True}
        import shared_media
        with patch.object(shared_media,'send_photo',return_value={'ok':True}) as delivery:
            server.notification_delivery.install(scope)
            scope['digest']('pm')
            scope['retry_notifications']()
        pairs={(call.args[1],call.args[2]) for call in delivery.call_args_list}
        self.assertEqual(pairs,{(uid,photo) for uid in (11,42,-17) for photo in ('telegram-photo','max:image:max-token','second-photo')})
        self.assertEqual(delivery.call_count,9)
        first=[call.args[3] for call in delivery.call_args_list if '20:30 /' in call.args[3]]
        self.assertEqual(len(first),3)
        self.assertEqual(len(set(first)),1)

    def test_morning_report_includes_both_platforms_but_not_daily_photos(self):
        server.roster(-17,'MAX student')
        with server.conn() as c:
            for uid,photo in ((42,'tg-morning'),(-17,'max:image:morning')):
                c.execute("insert into morning_checkins(user_id,day,mood,photo,step) values (?,?,?,?,?)",(uid,server.today(),'Хороший',photo,'done'))
            c.execute('insert into daily_photos(user_id,day,photo,created) values(?,?,?,?)',(42,server.today(),'daily-photo',1))
        scope=vars(server).copy();scope['GROUP']='';scope['AI_KEY']=''
        import shared_media
        with patch.object(shared_media,'send_photo',return_value={'ok':True}) as delivery:
            server.notification_delivery.install(scope)
            scope['digest']('am')
        self.assertEqual({(x.args[1],x.args[2]) for x in delivery.call_args_list},{(u,p) for u in (11,42,-17) for p in ('tg-morning','max:image:morning')})
        captions=[x.args[3] for x in delivery.call_args_list if '10:00 /' in x.args[3]]
        self.assertEqual(len(captions),3);self.assertEqual(len(set(captions)),1)

    def test_photo_report_retries_only_failed_recipient(self):
        scope=vars(server).copy();scope['GROUP']='';scope['AI_KEY']=''
        import shared_media
        rows=[{'user_id':42,'name':'Матвей','photo':'max:image:source'}]
        with patch.object(shared_media,'send_photo',side_effect=lambda s,chat,*rest:{'ok':chat==11}) as first:
            server.notification_delivery.install(scope)
            scope['broadcast_checkin_photos'](rows,'am','10:00 / ИСТОРИИ ЭТОГО УТРА')
        self.assertEqual(first.call_count,2)
        with patch.object(shared_media,'send_photo',return_value={'ok':True}) as retry:
            scope['retry_notifications']()
            scope['retry_notifications']()
        self.assertEqual(retry.call_count,1);self.assertEqual(retry.call_args.args[1],42)

    def test_init_data_signature_and_expiry(self):
        import time
        pairs = {'auth_date': str(int(time.time())), 'user': json.dumps({'id': 42})}
        check = '\n'.join(k+'='+v for k,v in sorted(pairs.items()))
        key = hmac.new(b'WebAppData', server.TOKEN.encode(), hashlib.sha256).digest()
        pairs['hash'] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
        raw = urllib.parse.urlencode(pairs)
        self.assertEqual(server.telegram_user(raw), 42)
        self.assertIsNone(server.telegram_user(raw.replace('42', '43')))

    def test_digest_only_includes_shared_answers(self):
        with server.conn() as c:
            c.execute('insert into answers(user_id,period,day,choice,detail,published) values (?,?,?,?,?,?)', (42,'am',server.today(),'В кадре','Еду в Москву',1))
            c.execute('insert into answers(user_id,period,day,choice,detail,published) values (?,?,?,?,?,?)', (11,'am',server.today(),'Сонный','Секрет',0))
        with patch.object(server, 'send') as sent, patch.object(server, 'ai_digest', return_value=None):
            server.digest('am')
        message = sent.call_args.args[1]
        self.assertIn('Матвей', message)
        self.assertIn('Москву', message)
        self.assertNotIn('Секрет', message)

    def test_direct_start_onboards_student(self):
        with patch.object(server, 'send') as sent:
            server.bot_message({'chat': {'type': 'private'}, 'from': {'id': 99, 'first_name': 'Гость'}, 'text': '/start'})
        self.assertTrue(server.allowed(99))
        self.assertIn('Привет', sent.call_args.args[1])

    def test_auth_token_tampering(self):
        token = server.signed(42)
        self.assertEqual(server.user_from_token(token)['name'], 'Матвей')
        self.assertIsNone(server.user_from_token(token.replace('42.', '11.', 1)))

    def test_admin_connects_group(self):
        server.GROUP = ''
        with patch.object(server, 'send'):
            server.bot_message({'chat': {'type': 'supergroup','id':-10042}, 'from': {'id':11}, 'text':'/connect'})
        self.assertEqual(server.GROUP, '-10042')
        server.GROUP = ''
        server.init()
        self.assertEqual(server.GROUP, '-10042')

    def test_tip_falls_back_when_ai_unavailable(self):
        with patch.object(server,'make_daily',return_value=server.fallback_content('tip')),patch.object(server,'send') as sent:
            server.tip()
        text=sent.call_args.args[1]
        self.assertIn('15:00',text)
        self.assertIn('ПРИЁМ ДНЯ',text)

    def test_generated_daily_tip_cached_with_source(self):
        result={'title':'Новый приём','body':'Уточняй действие перед съёмкой и найди хороший план.','mode':'text','source':'https://blog.frame.io/camera-angle/' }
        with patch.object(server,'make_daily',return_value=result) as make:
            self.assertEqual(server.daily_content('tip',True),result)
            self.assertEqual(server.daily_content('tip',True),result)
        make.assert_called_once()

    def test_mission_uses_two_age_versions_and_rotates_response_mode(self):
        server.AI_KEY='testing-key'
        try:
            with patch.object(server,'creative_enabled',return_value=True),patch.object(server,'ai_json',return_value={'title':'Одна деталь — история','kids':'Найди интересный предмет рядом и покажи его одним кадром.','media':'Выбери деталь, которая меняет смысл сцены, и покажи её одним кадром.','mode':server.fallback_content('mission')['mode']}) as ai:
                item=server.daily_content('mission',True)
            self.assertNotEqual(item['body_kids'],item['body_media'])
            self.assertEqual(item['mode'],server.fallback_content('mission')['mode'])
            self.assertIn('direction_kids',ai.call_args.args[1])
            with patch.object(server,'send') as sent:
                server.BOTNAME='timecode_test_bot'
                server.mission()
            self.assertIn('Kids Lab:',sent.call_args.args[1])
            self.assertIn('Media Lab:',sent.call_args.args[1])
        finally:
            server.AI_KEY=''
            server.BOTNAME=''

    def test_existing_database_migrates_mission_columns(self):
        with server.conn() as c:
            c.execute('alter table daily_content drop column body_kids')
            c.execute('alter table daily_content drop column body_media')
        server.init()
        with server.conn() as c:
            cols={row['name'] for row in c.execute('pragma table_info(daily_content)')}
        self.assertTrue({'body_kids','body_media'} <= cols)

    def test_ai_searches_source_and_generates_new_tip(self):
        server.AI_KEY='testing-key'
        with patch.object(server,'creative_enabled',return_value=True), patch.object(server,'industry_search',return_value={'title':'Camera angle','snippet':'A camera angle refers to the placement of a film camera in relation to the subject.','url':'https://www.studiobinder.com/blog/camera-angle/'}) as lookup,patch.object(server,'ai_json',side_effect=[{'query':'camera angle cinematography'},{'title':'Выбери ракурс','body':'Ракурс камеры меняет точку зрения на героя. Выбери его прежде, чем нажать запись.'},{'ok':True}]) as model:
            item=server.make_daily('tip')
        self.assertEqual(lookup.call_args.args[0],'camera angle cinematography')
        self.assertEqual(model.call_count,3)
        self.assertEqual(item['source'],'https://www.studiobinder.com/blog/camera-angle/')
        server.AI_KEY=''

    def test_tip_editor_rejects_non_actionable_reference(self):
        server.AI_KEY='testing-key'
        try:
            with patch.object(server,'creative_enabled',return_value=True), \
                 patch.object(server,'industry_search',return_value={'title':'Film review','snippet':'Camera tips for filming a scene with a phone in daylight.','url':'https://www.studiobinder.com/blog/camera-angle/'}), \
                 patch.object(server,'ai_json',side_effect=[{'query':'phone filming technique'}, {'title':'Отсылка к сериалу','body':'Вспомни любимый сериал и снимай как там. Получится красиво и интересно.'}, {'ok':False}]):
                item=server.make_daily('tip')
            self.assertEqual(item['source'],'')
            self.assertNotIn('сериалу',item['body'])
        finally:server.AI_KEY=''

    def test_search_excludes_sites_outside_film_sources(self):
        server.AI_KEY='testing-key'
        pages={'search_results':[{'title':'Fake','url':'https://example.com/trick','chunks':[{'text':'x'*150}]},{'title':'Film craft','url':'https://blog.frame.io/film-craft/','chunks':[{'text':'The operator plans the movement before the shot, choosing the starting position and ending position so the action remains legible.'}]}]}
        with patch.object(server.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(pages).encode())) as request:
            found=server.industry_search('filming movement',('blog.frame.io',))
        self.assertEqual(found['url'],'https://blog.frame.io/film-craft/')
        self.assertEqual(request.call_args.args[0].full_url,'https://api.moonshot.ai/v1/tools/search_pro')
        server.AI_KEY=''

    def test_student_question_admin_reply(self):
        with patch.object(server,'send',return_value={'ok':True,'result':{'message_id':77}}) as sent:
            server.bot_message({'chat':{'type':'private'},'from':{'id':42},'text':'/ask Как подготовиться к съёмке?'})
            self.assertIn('ВОПРОС #1',sent.call_args_list[0].args[1])
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'text':'Заряди камеру и проверь звук.','reply_to_message':{'message_id':77}})
        self.assertTrue(any(call.args[0]==42 and 'Заряди камеру' in call.args[1] for call in sent.call_args_list))
        with server.conn() as c:self.assertEqual(c.execute('select answered from questions where id=1').fetchone()['answered'],1)

    def test_question_in_group_is_forwarded(self):
        with patch.object(server,'send',return_value={'ok':True,'result':{'message_id':11}}) as sent:
            server.bot_message({'chat':{'type':'supergroup','id':-10042},'from':{'id':42},'text':'/ask@timecode_bot Можно снять интервью завтра?'})
        self.assertTrue(any(c.args[0]==11 and 'интервью завтра' in c.args[1] for c in sent.call_args_list))

    def test_admin_media_broadcast(self):
        with patch.object(server,'api',return_value={'ok':True}) as tg,patch.object(server,'send',return_value={'ok':True}):
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'caption':'/send Смотрите кадр','photo':[{'file_id':'small'},{'file_id':'large'}]})
        self.assertEqual(tg.call_args.args[0],'sendPhoto')
        self.assertEqual(tg.call_args.args[1]['photo'],'large')
        self.assertNotIn('/send',tg.call_args.args[1]['caption'])

    def test_admin_publish_button_and_ai_switch(self):
        with patch.object(server,'api',return_value={}),patch.object(server,'send',return_value={'ok':True}) as sent:
            server.callback({'id':'callback','from':{'id':11},'data':'admin:publish','message':{'chat':{'id':11}}})
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'text':'Завтра съёмка в студии'})
            self.assertTrue(any(c.args[0]=='-10042' and 'Завтра съёмка' in c.args[1] for c in sent.call_args_list))
            server.bot_message({'chat':{'type':'private'},'from':{'id':11},'text':'/ai off'})
        self.assertFalse(server.creative_enabled())
        with patch.object(server,'ai_json') as ai:
            self.assertEqual(server.make_daily('tip'),server.fallback_content('tip'))
        ai.assert_not_called()

    def test_subscriber_report_lists_platform_and_excludes_admin(self):
        server.roster(-63,'Ученик MAX')
        with server.conn() as c:c.execute('update users set enabled=0 where id=-63')
        with patch.object(server,'send') as delivered:
            server.subscriber_report(11)
        report=delivered.call_args.args[1]
        self.assertIn('Всего: <b>2</b> · Telegram: 1 · MAX: 1',report)
        self.assertIn('Ученик MAX · MAX',report)
        self.assertIn('Матвей · Telegram',report)
        self.assertNotIn('Дмитрий',report)
        self.assertNotIn('Отключены:',report)

    def test_broadcast_reaches_student_who_disabled_checkins(self):
        with server.conn() as c:c.execute('update users set enabled=0 where id=42')
        with patch.object(server,'send',return_value={'ok':True}) as delivered:
            sent,failed=server.publish_to_all({'text':'Занятие завтра'},'Занятие завтра')
        self.assertGreaterEqual(sent,1)
        self.assertEqual(failed,0)
        self.assertTrue(any(call.args[0]==42 for call in delivered.call_args_list))

    def test_admin_menu_persistent_button_is_private(self):
        with patch.object(server,'api',return_value={'ok':True}) as request:
            server.admin_menu(11)
            server.admin_menu(42)
        self.assertEqual(request.call_count,1)
        self.assertEqual(request.call_args.args[1]['chat_id'],11)
        self.assertTrue(request.call_args.args[1]['reply_markup']['is_persistent'])

    def test_checkin_cannot_be_disabled_and_old_opt_out_is_restored(self):
        with patch.object(server,'send') as delivered:
            server.bot_message({'chat':{'type':'private'},'from':{'id':42},'text':'/quiet'})
        with server.conn() as c:
            self.assertEqual(c.execute('select enabled from users where id=42').fetchone()['enabled'],1)
            c.execute('update users set enabled=0 where id=42')
        server.init()
        with server.conn() as c:
            self.assertEqual(c.execute('select enabled from users where id=42').fetchone()['enabled'],1)
        self.assertIn('пропусти',delivered.call_args.args[1])

    def test_student_asks_bot_without_sending_every_message_to_teacher(self):
        with patch.object(server,'send') as delivered, patch.object(server,'ask_admins') as forwarded:
            server.bot_message({'chat':{'type':'private'},'from':{'id':42},'text':'Что ты умеешь?'})
        message=delivered.call_args.args[1]
        self.assertIn('игры',message)
        self.assertIn('расписание',message)
        self.assertIn('отвечаю на вопросы',message)
        forwarded.assert_not_called()

    def test_student_gets_kimi_answer_and_fallback(self):
        old=server.AI_KEY
        server.AI_KEY='test'
        try:
            with patch.object(server,'ai_json',return_value={'text':'Попробуй снять с уровня глаз.'}):
                self.assertIn('уровня глаз',server.chat_reply('Как снять интервью?'))
            with patch.object(server,'ai_json',return_value=None):
                self.assertIn('Попробуй ещё раз',server.chat_reply('Как снять интервью?'))
        finally:server.AI_KEY=old

    def test_weekly_survey_runs_three_steps_and_notifies_admin(self):
        with patch.object(server,'api',return_value={'ok':True}), patch.object(server,'send',return_value={'ok':True}) as sent:
            server.callback({'id':'callback','from':{'id':42},'data':'weekly:start','message':{'chat':{'id':42}}})
            for reply in ('Сняли репортаж','Хочу узнать про монтаж','Нужна раскадровка'):
                server.bot_message({'chat':{'type':'private'},'from':{'id':42},'text':reply})
        with server.conn() as c:
            row=c.execute('select * from weekly_surveys where user_id=42 and week=?',(server.survey_week(),)).fetchone()
        self.assertEqual(row['step'],'done')
        self.assertEqual(row['feature'],'Нужна раскадровка')
        self.assertTrue(any(c.args[0]==11 and 'Нужна раскадровка' in c.args[1] for c in sent.call_args_list))

    def test_daily_photo_is_taken_once_and_published_immediately(self):
        photo={'photo':[{'file_id':'tg-photo-id'}]}
        with patch.object(server.threading,'Thread') as worker, patch.object(server,'send',return_value={'ok':True}):
            server.accept_daily_photo(42,photo)
            server.accept_daily_photo(42,photo)
        self.assertEqual(worker.call_count,1)
        with patch.object(server,'photo_comment',return_value='Свет мягкий и лицо читается. Фон успел причесаться раньше героя.'),patch.object(server,'send_attachment',return_value={'ok':True}) as media,patch.object(server,'send',return_value={'ok':True}):
            server.publish_daily_photo(42,server.today())
        self.assertTrue(any(c.args[0]==42 and 'Свет мягкий' in c.args[2] for c in media.call_args_list))
        with server.conn() as c:
            self.assertEqual(c.execute('select status from daily_photos where user_id=42').fetchone()['status'],'done')

    def test_daily_photo_never_sends_caption_without_photo_to_other_platform(self):
        server.roster(-17,'MAX student')
        with server.conn() as c:
            c.execute('insert into daily_photos(user_id,day,photo,created) values (?,?,?,0)',
                      (42,server.today(),'telegram-photo'))
        with patch.object(server,'photo_comment',return_value='Комментарий к кадру'), \
             patch.object(server,'send_attachment',return_value={'ok':True}) as telegram_photo, \
             patch.object(server,'send') as text_only, \
             patch.object(server.max_transport,'send_image') as max_photo:
            server.publish_daily_photo(42,server.today())
        self.assertFalse(text_only.called)
        self.assertFalse(max_photo.called)
        self.assertTrue(any(call.args[0]==42 for call in telegram_photo.call_args_list))
        with server.conn() as c:
            c.execute('insert into daily_photos(user_id,day,photo,created) values (?,?,?,0)',
                      (-17,server.today(),'max:image:token'))
        old_token=server.MAX_TOKEN
        server.MAX_TOKEN='max-test'
        try:
            with patch.object(server,'photo_comment',return_value='Комментарий к кадру'), \
                 patch.object(server,'send_attachment') as telegram_photo, \
                 patch.object(server,'send') as text_only, \
                 patch.object(server.max_transport,'send_image',return_value={'ok':True}) as max_photo:
                server.publish_daily_photo(-17,server.today())
            self.assertFalse(text_only.called)
            self.assertFalse(telegram_photo.called)
            max_photo.assert_called_once()
        finally:server.MAX_TOKEN=old_token


if __name__ == '__main__':
    unittest.main()
