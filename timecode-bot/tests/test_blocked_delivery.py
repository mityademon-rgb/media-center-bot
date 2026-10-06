import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from test_server import server
import notification_delivery
class BlockedDeliveryTests(unittest.TestCase):
    def test_blocked_terminal_transient_retry_and_incoming_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            server.DB=Path(directory)/'test.db';server.init()
            send=Mock(return_value={'ok':False,'error_code':403,'description':'Forbidden: bot was blocked by the user'})
            s=vars(server).copy();s.update(send=send,bot_message=Mock())
            notification_delivery.install(s)
            day=server.today();chat=json.dumps(42)
            with server.conn() as c:
                c.execute('insert into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(day,'blocked',chat,'text','null'))
                c.execute('insert into notification_photo_outbox(day,period,chat,user_id,photo,caption) values(?,?,?,?,?,?)',(day,'pm',chat,42,'photo','caption'))
            s['retry_notifications']()
            with server.conn() as c:
                self.assertEqual(c.execute('select delivered from notification_outbox').fetchone()[0],-1)
                self.assertEqual(c.execute('select delivered from notification_photo_outbox').fetchone()[0],-1)
                c.execute('insert into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(day,'next',chat,'text','null'))
            s['retry_notifications']();self.assertEqual(send.call_count,1)
            s['bot_message']({'from':{'id':42},'chat':{'type':'private'},'text':'/start'})
            send.return_value={'ok':False,'error_code':429,'description':'Too Many Requests'}
            with server.conn() as c:c.execute('insert into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',(day,'transient',chat,'text','null'))
            s['retry_notifications']()
            with server.conn() as c:self.assertEqual(c.execute("select delivered from notification_outbox where message_key='transient'").fetchone()[0],0)
            send.return_value={'ok':True};s['retry_notifications']()
            with server.conn() as c:self.assertEqual(c.execute("select delivered from notification_outbox where message_key='transient'").fetchone()[0],1)
if __name__=='__main__':unittest.main()
