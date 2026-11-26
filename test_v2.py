from contextlib import contextmanager
import tempfile,unittest,sqlite3,json,zipfile,hashlib
from pathlib import Path
from test_export import make_demo
from reader import open_archive,sessions,messages
from rich_export import batch,FORMATS
from wx4.reader import Wx4Data
@contextmanager
def db(path):
    c=sqlite3.connect(path)
    try:
        with c:yield c
    finally:c.close()

class Tests(unittest.TestCase):
    def test_formats_and_keyword(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);make_demo(p/'demo');d=open_archive(p/'demo')
            try:
                self.assertEqual(len(messages(d,'supplier_demo',full=True)),3)
                self.assertEqual(len(messages(d,'supplier_demo',full=True,keyword='delivery')),1)
                for f in FORMATS:
                    count,out,stats=batch(d,sessions(d),p/'out',f,full=True)
                    self.assertEqual(count,3);self.assertEqual(stats,{'not_requested':1});self.assertTrue(list(Path(out).rglob('chat.'+f)))
                    if f=='html':self.assertIn('สวัสดี',next(Path(out).rglob('chat.html')).read_text())
                count,out,stats=batch(d,sessions(d),p/'out','json',full=True,archive=True,keyword='delivery')
                with zipfile.ZipFile(out) as z:self.assertIsNone(z.testzip());self.assertEqual(json.loads(z.read('manifest.json'))['messages'],1)
            finally:d.close()
    def test_media_hash_and_quote(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);make_demo(p/'demo');account=p/'account';media=account/'msg'/'file';media.mkdir(parents=True);blob=b'hello attachment';(media/'test.txt').write_bytes(blob);h=hashlib.md5(blob).hexdigest();table=Wx4Data.msg_table_for('supplier_demo')
            with db(p/'demo'/'message_0.db') as c:
                c.execute(f'insert into {table} values (4,49,1795651400,?,1)',(f'<msg><appmsg><type>6</type><title>test.txt</title><appattach><filename>test.txt</filename><filemd5>{h}</filemd5></appattach></appmsg></msg>',))
                c.execute(f'insert into {table} values (5,49,1795651500,?,1)',('<msg><appmsg><type>57</type><title>Reply now</title><refermsg><displayname>Alice</displayname><content>Original</content><type>1</type></refermsg></appmsg></msg>',))
                c.execute(f'insert into {table} values (6,49,1795651600,?,1)',('<msg><appmsg><type>19</type><title>Forward</title><recorditem><![CDATA[<recordinfo><datalist><dataitem datatype="1"><sourcename>Alice</sourcename><datadesc>Forward text</datadesc></dataitem></datalist></recordinfo>]]></recorditem></appmsg></msg>',))
            d=open_archive(p/'demo')
            try:
                count,out,stats=batch(d,sessions(d),p/'out','json',True,True,account=account);self.assertEqual(count,6);self.assertEqual(stats['saved'],1);self.assertEqual(stats['missing'],1);rows=json.loads(next(Path(out).rglob('chat.json')).read_text())['messages'];self.assertIn('Original',rows[4]['text']);self.assertIn('Forward text',rows[5]['text']);self.assertEqual(next(Path(out).rglob('*test.txt')).read_bytes(),blob)
            finally:d.close()
    def test_cancel_removes_staging(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);make_demo(p/'demo');d=open_archive(p/'demo')
            try:
                def cancel():raise RuntimeError('cancelled')
                with self.assertRaisesRegex(RuntimeError,'cancelled'):batch(d,sessions(d),p/'out','html',cancel=cancel)
                self.assertEqual(list((p/'out').iterdir()),[])
            finally:d.close()
if __name__=='__main__':unittest.main()
