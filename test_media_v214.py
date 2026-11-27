import unittest, tempfile, hashlib, json
from pathlib import Path
from media_catalog import existing_account_image_keys

class ExistingAccessTests(unittest.TestCase):
    def test_only_exact_account_cache(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);account=root/'account';account.mkdir();wxid='demo_user'
            ident=hashlib.sha256((str(account.resolve())+'\0'+wxid).encode()).hexdigest()
            cache=root/'Moect'/'media-cache'/ident;cache.mkdir(parents=True)
            key=b'0123456789abcdef'
            (cache/'image-keys.json').write_text(json.dumps({'keys':[key.hex()],'xor':42}))
            result=existing_account_image_keys(account,wxid,localappdata=root)
            self.assertEqual(tuple(result),(key,));self.assertEqual(result.xor,42)
            self.assertFalse(existing_account_image_keys(account,'other_user',localappdata=root))
            self.assertFalse(existing_account_image_keys(root/'other_account',wxid,localappdata=root))
            (cache/'image-keys.json').write_text('invalid')
            self.assertFalse(existing_account_image_keys(account,wxid,localappdata=root))
    def test_cancel(self):
        with tempfile.TemporaryDirectory() as t:
            def stop():raise InterruptedError()
            with self.assertRaises(InterruptedError):existing_account_image_keys(t,'demo',stop,t)
