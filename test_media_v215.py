import io, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
from PIL import Image
from media_catalog import scan, export, image_result
from wx4.image_render import render_image, wxgf_first_frame

class RenderTests(unittest.TestCase):
    def test_raster_trailer_and_invalid(self):
        for fmt in ('JPEG','PNG','GIF','WEBP'):
            with self.subTest(fmt=fmt):
                b=io.BytesIO();Image.new('RGB',(16,16),'red').save(b,fmt);orig=b.getvalue()
                data,ext,q=render_image(orig+b'cache metadata')
                self.assertEqual(data,orig)
                self.assertEqual(q,'Raster image')
        with self.assertRaises(ValueError):render_image(b'\x89PNG\r\n\x1a\n')
    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg executable unavailable')
    def test_wxgf_hevc_first_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);raw=p/'frame.hevc'
            cmd=['ffmpeg','-nostdin','-loglevel','error','-f','lavfi','-i','color=red:s=64x48:r=1','-frames:v','1','-c:v','libx265','-x265-params','pools=1:frame-threads=1','-f','hevc',str(raw)]
            r=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
            if r.returncode:self.skipTest('HEVC encoder unavailable')
            src=p/'source';src.mkdir();(src/'sample.wxgf').write_bytes(b'wxgf'+raw.read_bytes())
            rows,errors=scan(src);self.assertEqual((len(rows),errors),(1,0));self.assertTrue(rows[0].available)
            data,ext,quality=image_result(rows[0]);self.assertEqual(ext,'.png');self.assertIn('first frame',quality)
            with Image.open(io.BytesIO(data)) as im:self.assertEqual(im.size,(64,48));self.assertGreater(im.getpixel((32,24))[0],200)
            out,n,skipped=export(rows,p/'out');self.assertEqual((n,skipped),(1,0));m=json.loads((Path(out)/'manifest.json').read_text());self.assertIn('first frame',m['files'][0]['quality'])
    def test_cancel(self):
        def stop():raise InterruptedError('cancel')
        with self.assertRaises(InterruptedError):wxgf_first_frame(b'wxgf',stop)
