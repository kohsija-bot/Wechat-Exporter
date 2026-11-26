import unittest,tempfile,json,base64
from pathlib import Path
from media_catalog import scan,export,image_bytes
from PIL import Image
from io import BytesIO
buffer=BytesIO();Image.new('RGB',(4,4),(32,64,128)).save(buffer,'PNG');PNG=buffer.getvalue()
MP4=b'\x00\x00\x00\x18ftypmp42'+b'\x00'*12 # classification fixture only, not playable
class Tests(unittest.TestCase):
    def test_scopes_and_export(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);src=p/'account';a=src/'msg'/'attach'/'chat1';a.mkdir(parents=True);v=src/'msg'/'video';v.mkdir(parents=True)
            (a/'sample.png').write_bytes(PNG);(a/'sample_thumb.png').write_bytes(PNG);(v/'clip.mp4').write_bytes(MP4);(a/'locked.dat').write_bytes(b'\x07\x08V2\x08\x07'+b'x'*50);(src/'unrelated.png').write_bytes(PNG)
            items,errors=scan(src,['msg/attach','msg/video']);self.assertEqual((len(items),errors),(4,0));self.assertEqual(sum(x.kind=='Video' for x in items),1);self.assertEqual(sum(x.thumbnail for x in items),1);self.assertEqual(sum(x.available for x in items),3)
            subset,_=scan(src,['msg/attach/chat1']);self.assertEqual(len(subset),3)
            out,saved,skipped=export(items,p/'out');self.assertEqual((saved,skipped),(3,1));d=Path(out);self.assertEqual(len(list((d/'Images').iterdir())),2);self.assertEqual(next((d/'Videos').iterdir()).read_bytes(),MP4);self.assertEqual(json.loads((d/'manifest.json').read_text())['skipped'],1)
            out2,*_=export(items,p/'out');self.assertNotEqual(out,out2)
    def test_extensionless_and_legacy(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'original').write_bytes(PNG);(p/'old.dat').write_bytes(bytes(x^0x45 for x in PNG));rows,errors=scan(p);self.assertEqual((len(rows),errors),(2,0));legacy=next(x for x in rows if x.status=='Legacy image');self.assertEqual(image_bytes(legacy),(PNG,'.png'))
            result,saved,skipped=export(rows,p/'result');self.assertEqual((saved,skipped),(2,0));self.assertTrue(all(x.read_bytes()==PNG for x in (Path(result)/'Images').iterdir()))
    def test_account_cache_and_unknown_suffix(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'cache'/'video').mkdir(parents=True); (p/'cache'/'image').mkdir(); (p/'db_storage').mkdir()
            (p/'cache'/'video'/'clip.unknown').write_bytes(MP4); (p/'cache'/'image'/'photo.thumb').write_bytes(PNG); (p/'cache'/'image'/'locked.bin').write_bytes(b'\x07\x08V2\x08\x07'+b'x'*50); (p/'db_storage'/'ignored.png').write_bytes(PNG)
            items,errors=scan(p); self.assertEqual((len(items),errors),(3,0)); self.assertEqual(sum(x.available for x in items),2); self.assertEqual(sum(x.kind=='Video' for x in items),1); self.assertIn('Encrypted V2 image',[x.status for x in items]); self.assertEqual(sum(x.thumbnail for x in items),1)
            out,saved,skipped=export(items,p/'out'); self.assertEqual((saved,skipped),(2,1)); self.assertEqual(next((Path(out)/'Videos').iterdir()).suffix,'.mp4')
    def test_cancel_and_changed_source(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);src=p/'src';src.mkdir();a=src/'img.png';a.write_bytes(PNG);items,_=scan(src)
            def cancel():raise RuntimeError('cancel')
            with self.assertRaisesRegex(RuntimeError,'cancel'):export(items,p/'out',cancel)
            self.assertEqual(list((p/'out').iterdir()),[]);a.write_bytes(PNG+b'changed');_,saved,skipped=export(items,p/'out');self.assertEqual((saved,skipped),(0,1))
    def test_duplicates_and_unverified(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);src=p/'src';(src/'a').mkdir(parents=True);(src/'b').mkdir();(src/'a'/'same.png').write_bytes(PNG);(src/'b'/'same.png').write_bytes(PNG);(src/'b'/'fake.jpg').write_bytes(b'not image');items,_=scan(src);self.assertEqual(sum(x.available for x in items),2);out,saved,skipped=export(items,p/'out');self.assertEqual((saved,skipped),(2,1));self.assertEqual(len(list((Path(out)/'Images').iterdir())),2)
if __name__=='__main__':unittest.main()
