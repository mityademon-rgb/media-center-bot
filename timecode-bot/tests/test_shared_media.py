import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_server import server
import shared_media


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        server.DB=Path(self.temp.name)/'bridge.db'
        server.init()
        with server.conn() as c:server.max_transport.link_identity(c,'max',17,-17)
        self.s=vars(server).copy()
        self.s.update(TOKEN='telegram-secret',MAX_TOKEN='max-secret')
        self.s['send_attachment']=Mock(return_value={'ok':True})

    def tearDown(self):self.temp.cleanup()

    def test_telegram_upload_to_max_cached_without_token_url_leak(self):
        self.s['api']=Mock(return_value={'ok':True,'result':{'file_path':'photos/file_1.jpg'}})
        with patch.object(shared_media,'request',side_effect=[b'image',b'{"photos":{"one":{"token":"uploaded-token"}}}']) as request, \
             patch.object(server.max_transport,'api',return_value={'url':'https://iu.oneme.ru/uploadImage?sig=test'}) as upload, \
             patch.object(server.max_transport,'send_image',return_value={'ok':True}) as send:
            shared_media.send_photo(self.s,-17,'tg-image','caption')
            shared_media.send_photo(self.s,-17,'tg-image','caption')
        self.assertEqual(request.call_count,2)
        self.assertEqual(upload.call_count,1)
        self.assertEqual(send.call_count,2)
        self.assertEqual(send.call_args.args[1],'uploaded-token')
        self.assertNotIn(b'telegram-secret',request.call_args.args[1])

    def test_max_image_to_telegram_cached_and_failed_send_not_cached(self):
        shared_media.remember(self.s,'max:image:source','https://i.mycdn.me/image.jpg')
        with patch.object(shared_media,'request',side_effect=[b'image',b'{"ok":false}',b'image',b'{"ok":true,"result":{"photo":[{"file_id":"tg-copy"}]}}']) as request:
            self.assertFalse(shared_media.send_photo(self.s,42,'max:image:source','caption')['ok'])
            self.assertTrue(shared_media.send_photo(self.s,42,'max:image:source','caption')['ok'])
            shared_media.send_photo(self.s,43,'max:image:source','caption')
        self.assertEqual(request.call_count,4)
        self.assertEqual(self.s['send_attachment'].call_args.args[1]['photo'][0]['file_id'],'tg-copy')

    def test_negative_telegram_group_is_not_max(self):
        with patch.object(server.max_transport,'send_image') as send:
            shared_media.send_photo(self.s,-100123,'tg-image','caption')
        send.assert_not_called()
        self.s['send_attachment'].assert_called_once()

    def test_untrusted_media_and_redirect_hosts_rejected(self):
        for url in ('http://iu.oneme.ru/a','https://127.0.0.1/a','https://oneme.ru.evil.test/a','https://user@iu.oneme.ru/a'):
            with self.assertRaises(ValueError):shared_media.trusted_url(url)
        self.assertEqual(shared_media.trusted_url('https://iu.oneme.ru/a'),'https://iu.oneme.ru/a')


if __name__=='__main__':unittest.main()
