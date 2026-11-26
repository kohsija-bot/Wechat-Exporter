from contextlib import contextmanager
import csv,json,sqlite3,tempfile,unittest,types,sys,os
from pathlib import Path
from unittest.mock import patch
import psutil,wx4,live
from test_export import make_demo
from reader import open_archive,sessions,messages
from exporter import export_chat
@contextmanager
def db(path):
    c=sqlite3.connect(path)
    try:
        with c:yield c
    finally:c.close()

class Tests(unittest.TestCase):
    def test_group_and_multiple_shards(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);make_demo(p)
            with db(p/'message_0.db') as c:
                t=c.execute("select name from sqlite_master where name like 'Msg_%'").fetchone()[0]
            with db(p/'message_1.db') as c:
                c.execute('create table Name2Id(user_name text)');c.execute("insert into Name2Id values ('me')")
                c.execute(f'create table {t}(local_id integer, local_type integer, create_time integer,message_content text,real_sender_id integer)')
                c.execute(f'insert into {t} values (4,1,1795651350,?,1)',('new message',))
            d=open_archive(p,'me')
            try:
                rows=messages(d,sessions(d)[0]['id']);self.assertEqual(len(rows),3);self.assertEqual(rows[-1]['sender'],'Me');self.assertEqual(rows[-1]['text'],'new message');self.assertEqual(len(messages(d,'supplier_demo',limit=2)),2)
            finally:d.close()
    def test_cancel_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);s={'id':'a','name':'A'};rows=[dict(timestamp='2026-01-01',sender='A',sender_id='a',text='=1+1')];first=export_chat(p,s,rows,'txt');before=first.read_bytes()
            def stop():raise RuntimeError('cancelled')
            with self.assertRaisesRegex(RuntimeError,'cancelled'):export_chat(p,s,rows,'txt',cancel=stop)
            self.assertEqual(list(p.iterdir()),[first]);self.assertEqual(first.read_bytes(),before)
            f=export_chat(p,s,rows,'csv')
            with f.open(encoding='utf-8-sig',newline='') as stream:self.assertEqual(list(csv.DictReader(stream))[0]['text'],"'=1+1")
            self.assertEqual(json.loads(export_chat(p,s,rows,'json').read_text())['messages'][0]['text'],'=1+1')
    def test_mocked_live_adapter_plain_database(self):
        # Exercise the connection/snapshot workflow, NOT real Windows process access or decryption.
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);storage=p/'account'/'db_storage';make_demo(storage)
            class FakeExtractor:
                def __init__(self,*a,**k):self.keys={};self.db_files=[];self.salt_index={}
                def collect(self):return []
                def extract(self):self.collect()
                def result_payload(self):return {}
            key=types.SimpleNamespace(find_weixin_processes=lambda:[{'pid':os.getpid()}],enable_debug_privilege=lambda:False,KeyExtractor=FakeExtractor)
            dec=types.SimpleNamespace(decrypt_all=lambda *a,**k:None)
            with patch.object(wx4,'key',key,create=True),patch.object(wx4,'decrypt',dec,create=True),patch.object(live.sys,'platform','win32'),patch.dict(os.environ,{'LOCALAPPDATA':str(p)}):
                root,wxid,warning=live.make_snapshot({'db_storage':str(storage),'wxid':'me'})
                self.assertEqual(wxid,'me');self.assertEqual(warning,'');self.assertNotEqual(Path(root),storage)
                d=open_archive(root,wxid)
                try:self.assertEqual(len(messages(d,'supplier_demo')),2)
                finally:d.close()
                self.assertTrue((storage/'message_0.db').exists());self.assertFalse(list(Path(root).rglob('keys.json')))
                (storage/'message_0.db').unlink()
                with self.assertRaisesRegex(RuntimeError,'Missing session or message'):live.make_snapshot({'db_storage':str(storage),'wxid':'me'})
    def test_live_unsupported_platform(self):
        if sys.platform!='win32':
            with self.assertRaisesRegex(RuntimeError,'Windows'):live.detect()
if __name__=='__main__':unittest.main()
