import unittest
from unittest.mock import Mock
import admin_controls


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.send=Mock();self.message=Mock();self.callback=Mock()
        self.s={'send':self.send,'bot_message':self.message,'callback':self.callback,'ADMINS':{11,-17}}
        admin_controls.install(self.s)

    def test_controls_on_every_teacher_reply_in_both_platforms(self):
        for uid in (11,-17):
            self.s['send'](uid,'Ответ')
            keys=self.send.call_args.args[2]
            self.assertEqual({b['callback_data'] for row in keys for b in row},
                             {'admin:publish','admin:subscribers:0','admin:schedule'})

    def test_preserves_existing_controls_without_duplicates(self):
        key=[[{'text':'Сохранить','callback_data':'sch:commit'},
              {'text':'Расписание','callback_data':'admin:schedule'}]]
        self.s['send'](11,'Ответ',key)
        keys=self.send.call_args.args[2]
        self.assertEqual(sum(b['callback_data']=='admin:schedule' for row in keys for b in row),1)
        self.assertEqual(len(key),1)

    def test_routes_teacher_button_before_quest(self):
        self.s['bot_message']({'from':{'id':11},'chat':{'type':'private'},'text':'📣 Написать всем'})
        self.callback.assert_called_once()
        self.message.assert_not_called()

    def test_student_does_not_get_teacher_controls(self):
        self.s['send'](42,'Ответ')
        self.assertIsNone(self.send.call_args.args[2])

    def test_group_message_does_not_route_private_teacher_action(self):
        self.s['bot_message']({'from':{'id':11},'chat':{'type':'group'},'text':'📣 Написать всем'})
        self.callback.assert_not_called()
        self.message.assert_called_once()
