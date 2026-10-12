import datetime as dt,html,json,sqlite3,tempfile,unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock,patch
import creative_digest as m
BODY='Массовка, у нас сегодня три зомби и ни одного специалиста по оживлению. Рюкзаки добрались до понедельника, владельцы пока загружаются. В 15:00 принесу лайфхак — попробуем хотя бы включить звук.'
class Editions(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'test.db'
  @contextmanager
  def conn():
   c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
   try:
    with c:yield c
   finally:c.close()
  self.conn=conn
  with conn() as c:
   c.executescript('create table daily_photos(user_id integer,day text,photo text,photo_url text,comment text,status text);create table users(id integer,name text);create table photo_hunts(user_id integer,day text,period text,task text,comment text);create table sent(slot text,day text,primary key(slot,day));create table notification_outbox(day text,message_key text,chat text,body text,keyboard text,delivered integer default 0,primary key(day,message_key,chat));');m.tables(c)
  self.s={'conn':conn,'today':lambda:'2026-10-12','now':lambda:dt.datetime(2026,10,12,10),'AI_KEY':'test','ai_json':Mock(side_effect=[{'text':BODY,'captions':[]},{'ok':True}]),'photo_comment':Mock(return_value='Кружка снята снизу, длинная тень и чистый фон.'),'ADMINS':{11,-12},'esc':html.escape,'retry_notifications':Mock(),'class_reminders':Mock()}
  self.rows=[{'user_id':42,'name':'Саша','mood':'Зомби','important':'','photo':''}];self.old=m.editorial_voice.story;self.cap=getattr(m.editorial_voice,'digest_caption',None)
 def tearDown(self):
  m.editorial_voice.story=self.old
  if self.cap is None:
   if hasattr(m.editorial_voice,'digest_caption'):del m.editorial_voice.digest_caption
  else:m.editorial_voice.digest_caption=self.cap
  self.tmp.cleanup()
 def test_cache_after_validated_generation(self):
  self.assertEqual(m.render(self.s,self.rows,True),BODY);self.assertEqual(m.render(self.s,self.rows,True),BODY);self.assertEqual(self.s['ai_json'].call_count,2)
 def test_api_failure_no_template(self):
  self.s['ai_json']=Mock(return_value=None)
  with self.assertRaises(m.EditorialPending):m.render(self.s,self.rows,True)
  with self.conn() as c:self.assertEqual(c.execute('select count(*) from kimi_editions').fetchone()[0],0)
 def test_old_template_rejected(self):
  self.s['ai_json']=Mock(return_value={'text':'Друзья, прочитал ваши утренние ответы. '+BODY,'captions':[]})
  with self.assertRaises(m.EditorialPending):m.render(self.s,self.rows,True)
 def test_editor_revision(self):
  self.s['ai_json']=Mock(side_effect=[{'text':BODY,'captions':[]},{'ok':False,'reason':'выдуман отдых'},{'text':BODY,'captions':[]},{'ok':True}]);m.render(self.s,self.rows,True);self.assertIn('выдуман отдых',self.s['ai_json'].call_args_list[2].args[0])
 def test_each_frame_caption_persisted(self):
  self.rows[0]['photo']='p';k=m.photo_key(42,'p');self.s['ai_json']=Mock(side_effect=[{'text':BODY,'captions':[{'key':k,'text':'Саша. Кружка снята снизу — выглядит начальником кухни. На планёрку к ней не пойду.'}]},{'ok':True}]);self.s['digest']=Mock()
  with self.conn() as c:c.execute("insert into photo_hunts values(42,'2026-10-12','am','Сними кружку','Кружка снята снизу, длинная тень и чистый фон.')")
  m.install(self.s);m.render(self.s,self.rows,True);self.assertIn('Кружка',m.editorial_voice.digest_caption(self.s,self.rows[0],'am'))
 def test_unseen_frame_blocks(self):
  self.rows[0]['photo']='p';self.s['photo_comment']=Mock(return_value='')
  with self.assertRaises(m.EditorialPending):m.render(self.s,self.rows,True)
  self.s['ai_json'].assert_not_called()
 def test_retries_restart_alert_once_and_cooldown(self):
  self.s['digest']=Mock(side_effect=m.EditorialPending('kimi-api'));m.install(self.s)
  with patch.object(m.time,'time',return_value=100):self.s['digest']('am')
  t=dict(self.s);t['digest']=Mock(side_effect=m.EditorialPending('kimi-api'));t['class_reminders']=Mock();m.install(t)
  for tm in (129,130,220,1120):
   with patch.object(m.time,'time',return_value=tm):t['kimi_edition_retry']()
  with self.conn() as c:
   self.assertEqual(c.execute('select attempts from kimi_edition_jobs').fetchone()[0],4);self.assertEqual(c.execute('select count(*) from notification_outbox').fetchone()[0],2)
 def test_recovered_job_not_repeated(self):
  old=Mock(side_effect=[m.EditorialPending('api'),None]);self.s['digest']=old;m.install(self.s)
  with patch.object(m.time,'time',return_value=100):self.s['digest']('pm')
  with patch.object(m.time,'time',return_value=130):self.s['kimi_edition_retry']();self.s['digest']('pm')
  self.assertEqual(old.call_count,2)
  with self.conn() as c:self.assertEqual(c.execute('select status from kimi_edition_jobs').fetchone()[0],'done')
 def test_awards_preserved(self):
  self.s['digest']=Mock();self.s['status_settle']=Mock(return_value='Награда Саше');m.install(self.s);self.assertIn('Награда Саше',m.editorial_voice.story(self.s,self.rows,False))
 def test_empty_round_still_authored(self):m.render(self.s,[],True);self.assertEqual(self.s['ai_json'].call_count,2)
 def test_platform_frame_identity(self):self.assertNotEqual(m.photo_key(17,'same'),m.photo_key(-17,'same'))
if __name__=='__main__':unittest.main()

class Delivery(Editions):
 def test_story_and_individual_photos_reach_both_platforms_once(self):
  import notification_delivery,shared_media
  with self.conn() as c:
   c.executescript("create table morning_checkins(user_id integer,day text,sleep text,mood text,important text,photo text,step text);create table notification_photo_outbox(day text,period text,chat text,user_id integer,photo text,caption text,delivered integer default 0,primary key(day,period,chat,user_id));alter table users add column enabled integer default 1;")
   c.executemany('insert into users(id,name) values(?,?)',[(42,'Саша'),(-17,'Матвей')])
   c.execute("insert into morning_checkins values(42,'2026-10-12','','Зомби','','photo','done')")
   c.execute("insert into photo_hunts values(42,'2026-10-12','am','Сними кружку','Кружка снята снизу, длинная тень и чистый фон.')")
  self.s.update(evening=Mock(),instant_photo=Mock(),bot_message=Mock(),send=Mock(return_value={'ok':True}),api=Mock(),GROUP='',BOTNAME='bot',MAX_TOKEN='',make_daily=Mock())
  k=m.photo_key(42,'photo');self.s['ai_json']=Mock(side_effect=[{'text':BODY,'captions':[{'key':k,'text':'Саша. Кружка снята снизу — начальник всей кухни. На планёрку к ней не пойду.'}]},{'ok':True}])
  notification_delivery.install(self.s);m.install(self.s)
  with patch.object(shared_media,'send_photo',return_value={'ok':True}) as photo:
   self.s['digest']('am');self.s['digest']('am')
   self.assertEqual(photo.call_count,2)
   self.assertTrue(all('Кружка' in call.args[3] for call in photo.call_args_list))
  with self.conn() as c:
   self.assertEqual(c.execute('select count(*) from notification_outbox where delivered=1').fetchone()[0],2)
   self.assertEqual(c.execute('select count(*) from notification_photo_outbox where delivered=1').fetchone()[0],2)
   self.assertEqual(c.execute('select status from kimi_edition_jobs').fetchone()[0],'done')

class Vision(Editions):
 def test_uses_real_bridge_bytes_and_validated_observation(self):
  with self.conn() as c:
   c.execute('create table shared_photo_assets(photo text,url text)');c.execute("insert into shared_photo_assets values('p','')")
  self.s['VISION_MODEL']='kimi-k2.6';self.s['kimi_request']=Mock(return_value={'choices':[{'message':{'content':json.dumps({'visible':True,'observation':'Красная кружка снята снизу на чистом фоне.','comment':'Она явно управляет кухней.'})}}]})
  with patch.object(m.shared_media,'remember'),patch.object(m.shared_media,'download',return_value=b'\xff\xd8actual-bytes'):
   self.assertIn('Красная кружка',m.inspect_photo(self.s,'p'))
  payload=self.s['kimi_request'].call_args.args[1]
  self.assertTrue(payload['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,'))
 def test_invisible_photo_never_invents_observation(self):
  with self.conn() as c:c.execute('create table shared_photo_assets(photo text,url text)')
  self.s['VISION_MODEL']='kimi-k2.6';self.s['kimi_request']=Mock(return_value={'choices':[{'message':{'content':'{"visible":false}'}}]})
  with patch.object(m.shared_media,'remember'),patch.object(m.shared_media,'download',return_value=b'\xff\xd8actual-bytes'):
   with self.assertRaises(m.EditorialPending):m.inspect_photo(self.s,'p')

class Reviewer(Editions):
 def test_truncated_review_is_explicit_retry_reason(self):
  self.s['ai_json']=Mock(side_effect=[{'text':BODY,'captions':[]},None])
  with self.assertRaisesRegex(m.EditorialPending,'kimi-review-json-unavailable'):m.render(self.s,self.rows,True)
  self.assertGreaterEqual(self.s['ai_json'].call_args.args[2],1000)
  with self.conn() as c:self.assertEqual(c.execute('select count(*) from kimi_editions').fetchone()[0],0)

class Provider(Editions):
 def test_provider_http_error_is_not_swallowed(self):
  self.s.update(AI_MODEL='kimi-k2.6',AI_API='https://example.invalid')
  with patch.object(m.subprocess,'run',return_value=Mock(returncode=0,stdout='{"error":{}}\n429')):
   with self.assertRaisesRegex(m.EditorialPending,'kimi-http-429'):m.provider_json(self.s,'check','{}',1200)
 def test_provider_truncation_is_explicit(self):
  self.s.update(AI_MODEL='kimi-k2.6',AI_API='https://example.invalid')
  payload={'choices':[{'finish_reason':'length','message':{'content':'{"ok":false,"reason":"'}}]}
  with patch.object(m.subprocess,'run',return_value=Mock(returncode=0,stdout=json.dumps(payload)+'\n200')):
   with self.assertRaisesRegex(m.EditorialPending,'kimi-json-truncated'):m.provider_json(self.s,'check','{}',1200)
