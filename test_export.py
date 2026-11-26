from contextlib import contextmanager
import tempfile,sqlite3,unittest,json,csv
from pathlib import Path
from reader import open_archive,sessions,messages
from exporter import export_chat
from wx4.reader import Wx4Data

@contextmanager
def db(path):
    c=sqlite3.connect(path)
    try:
        with c:yield c
    finally:c.close()

def make_demo(p):
    p=Path(p);p.mkdir(parents=True,exist_ok=True)
    with db(p/'session.db') as c:
        c.execute('create table SessionTable(username text,last_timestamp integer)');c.execute('insert into SessionTable values (?,?)',('supplier_demo',1795651200))
    with db(p/'contact.db') as c:
        c.execute('create table contact(username text,nick_name text)');c.executemany('insert into contact values (?,?)',[('supplier_demo','Demo Supplier'),('me','Demo User')])
    with db(p/'message_0.db') as c:
        c.execute('create table Name2Id(user_name text)');c.executemany('insert into Name2Id values (?)',[('supplier_demo',),('me',)])
        t=Wx4Data.msg_table_for('supplier_demo');c.execute(f'create table {t}(local_id integer, local_type integer, create_time integer, message_content text, real_sender_id integer)');c.executemany(f'insert into {t} values (?,?,?,?,?)',[(1,1,1795651200,'你好 — สวัสดี — Hello',1),(2,1,1795651260,'Please confirm delivery.',2),(3,3,1795651320,'image',1)])
class Test(unittest.TestCase):
    def test_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);make_demo(p/'demo');d=open_archive(p/'demo')
            try:
                s=sessions(d)[0];r=messages(d,s['id']);self.assertEqual(len(r),2);self.assertEqual(r[0]['sender'],'Demo Supplier');self.assertIn('สวัสดี',r[0]['text']);self.assertEqual(len(messages(d,s['id'],limit=1)),1);self.assertEqual(len(messages(d,s['id'],start=1795651260)),1)
                for fmt in ('txt','md','csv','json'):
                    path=export_chat(p,s,r,fmt);self.assertIn('สวัสดี',path.read_text(encoding='utf-8-sig'));self.assertNotEqual(path,export_chat(p,s,r,fmt))
            finally:d.close()
if __name__=='__main__':unittest.main()
