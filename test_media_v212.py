import unittest,tempfile,json,struct,importlib.util,sqlite3
from pathlib import Path
from media_catalog import scan,export,image_bytes,load_image_keys,validate_raster,V2
from test_media_catalog import PNG
from test_export import make_demo
from reader import open_archive,messages

class Tests(unittest.TestCase):
    def test_import_and_wrong_key(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); key=b'0123456789abcdef'; f=p/'key.json';f.write_text(json.dumps({'keys':[key.hex()]}));self.assertEqual(load_image_keys(f),(key,));f.write_text('{}');self.assertRaises(ValueError,load_image_keys,f)
    def test_real_raster_validation(self):
        validate_raster(PNG)
        with self.assertRaises(ValueError):validate_raster(PNG[:20])
    def test_scan_cancellation(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'a.png').write_bytes(PNG)
            def stop():raise RuntimeError('stop')
            with self.assertRaisesRegex(RuntimeError,'stop'):scan(p,cancel=stop)
    def test_message_query_cancel_and_reuse(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);make_demo(p);data=open_archive(p)
            try:
                def stop():raise RuntimeError('stop')
                with self.assertRaisesRegex(RuntimeError,'stop'):messages(data,'supplier_demo',cancel=stop)
                self.assertEqual(len(messages(data,'supplier_demo')),2)
            finally:data.close()
    @unittest.skipUnless(importlib.util.find_spec('Cryptodome'),'Cryptodome not installed in this test environment')
    def test_v2_known_key(self):
        from Cryptodome.Cipher import AES
        key=b'0123456789abcdef'; prefix=PNG[:32];suffix=PNG[32:];pad=b'\x10'*16
        payload=V2+struct.pack('<LLB',len(prefix),0,0)+AES.new(key,AES.MODE_ECB).encrypt(prefix+pad)+suffix
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'image.dat').write_bytes(payload);rows,_=scan(p,keys=(key,));self.assertEqual(image_bytes(rows[0],(key,)),(PNG,'.png'))
            with self.assertRaises(ValueError):image_bytes(rows[0],(b'x'*16,))
            out,saved,skipped=export(rows,p/'out',keys=(key,));self.assertEqual((saved,skipped),(1,0));self.assertEqual(next((Path(out)/'Images').iterdir()).read_bytes(),PNG)
if __name__=='__main__':unittest.main()
