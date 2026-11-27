import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import media_catalog as c
from test_media_catalog import PNG, MP4

class MediaHotfix(unittest.TestCase):
    def test_diagnostic_shaped_scan(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            for folder,n,data,suffix in [('msg/attach',77,c.V2+b'x'*50,'.dat'),('cache',24,c.V2+b'x'*50,'.dat'),('msg/video',6,MP4,'.mp4'),('msg/video',15,b'\xff\xd8\xff'+b'x'*60,'.jpg'),('cache',1,PNG,'.none')]:
                d=base/folder;d.mkdir(parents=True,exist_ok=True)
                for i in range(n): (d/(str(i)+suffix)).write_bytes(data)
            d=base/'business/emoticon';d.mkdir(parents=True)
            for i in range(12):(d/str(i)).write_bytes(b'not media')
            (base/'unrelated').mkdir();(base/'unrelated'/'ignore.png').write_bytes(PNG)
            rows,errors=c.scan(base,c.ACCOUNT_MEDIA_FOLDERS)
            self.assertEqual((len(rows),errors),(123,0))
            self.assertEqual(sum(r.status=='Encrypted V2 image' for r in rows),101)
            self.assertEqual(sum(r.kind=='Video' for r in rows),6)
            self.assertEqual(sum(r.status=='Ready' for r in rows),22)
            self.assertFalse(any('unrelated' in r.relative for r in rows))
    def test_import_xor_and_reclassify_without_io(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);key=b'0123456789abcdef';f=p/'key.json';f.write_text(json.dumps({'keys':[key.hex()],'xor':42}));keys=c.load_image_keys(f)
            self.assertEqual(keys,(key,));self.assertEqual(keys.xor,42)
            x=c.Media('unused','a.dat','Image','.dat','Encrypted V2 image',100,0)
            self.assertEqual(c.with_keys(x,keys).status,'V2 key supplied')
            for bad in [-1,256,True,'42']:
                f.write_text(json.dumps({'keys':[key.hex()],'xor':bad}))
                with self.assertRaises(ValueError):c.load_image_keys(f)
    @unittest.skipUnless(importlib.util.find_spec('Cryptodome'),'Cryptodome not installed')
    def test_supplied_xor_for_valid_webp(self):
        import struct
        from Cryptodome.Cipher import AES
        from PIL import Image
        from io import BytesIO
        out=BytesIO();Image.new('RGB',(4,4),(20,50,80)).save(out,'WEBP');raw=out.getvalue()
        key=b'0123456789abcdef';prefix=raw[:32];tail=raw[32:];xor=42
        encrypted=c.V2+struct.pack('<LLB',len(prefix),len(tail),0)+AES.new(key,AES.MODE_ECB).encrypt(prefix+b'\x10'*16)+bytes(x^xor for x in tail)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'a.dat').write_bytes(encrypted);rows,_=c.scan(p,keys=c.ImageKeys([key],xor))
            self.assertEqual(c.image_bytes(rows[0],c.ImageKeys([key],xor)),(raw,'.webp'))
            with self.assertRaises(ValueError):c.image_bytes(rows[0],(key,))
    @unittest.skipUnless(importlib.util.find_spec('PySide6'),'PySide6 not installed')
    def test_qdialog_worker_finishes(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QEventLoop,QTimer
        from media_browser import MediaBrowser
        app=QApplication.instance() or QApplication([])
        dlg=MediaBrowser(); results=[]
        dlg.start_job(lambda c,p,s:'ok',results.append)
        self.assertIsNotNone(dlg.worker)
        loop=QEventLoop();timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:loop.quit() if dlg.worker is None else None);timer.start();QTimer.singleShot(5000,loop.quit);loop.exec();timer.stop()
        self.assertIsNone(dlg.worker);self.assertEqual(results,['ok']);dlg.close()
