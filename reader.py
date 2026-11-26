"""Read an existing decrypted Moect archive, without touching live WeChat."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import heapq
from collections import deque
from wx4.reader import Wx4Data

TZ = None  # Use the operating system local time zone, including DST.
FIELDS = ('local_id','server_id','local_type','sort_seq','real_sender_id','create_time','message_content','compress_content','packed_info_data')

def open_archive(root, wxid="", account_dir=None, cancel=lambda:None):
    p=Path(root)
    if not p.is_dir(): raise ValueError('Select a valid archive folder.')
    cancel();candidates=list(p.rglob('session.db'))
    if len(candidates)>1: raise ValueError('Multiple snapshots found. Select one snapshot folder, not its parent.')
    if not candidates: raise ValueError('No session.db found. Select a readable chat snapshot.')
    with candidates[0].open('rb') as f:
        if f.read(16)!=b'SQLite format 3\0': raise ValueError('This database is encrypted. A decrypted archive is required.')
    for db in list(p.rglob('message_*.db'))+list(p.rglob('biz_message_*.db')):
        cancel()
        with db.open('rb') as f:
            if f.read(16)!=b'SQLite format 3\0': raise ValueError('Encrypted message database found. Select a decrypted snapshot.')
    data=Wx4Data(str(p), wxid=wxid, account_dir=account_dir,cancel=cancel)
    try:
        if not data.msg_dbs: raise ValueError('No readable message databases found.')
        if any(c is None for c in data._conns.values()): raise ValueError('One or more database files could not be opened. Check the archive.')
        return data
    except BaseException:
        data.close(); raise

def sessions(data,cancel=lambda:None):
    result=[]
    for r in data.sessions():
        cancel()
        if data.has_messages(r['username']):result.append(dict(id=r['username'],name=r['display'],group=r['username'].endswith('@chatroom')))
    return result

def iter_messages(data, uid, start=None, end=None, cancel=lambda:None, full=False, keyword="", media=None, reverse=False):
    table=data.msg_table_for(uid)
    def shard_rows(shard,con):
        cancel()
        if table not in data.tables_of(con): return
        cols={r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
        if not {'local_id','local_type','create_time','message_content','real_sender_id'}<=cols: raise ValueError('Unsupported message table schema.')
        fields=','.join(f'"{c}"' if c in cols else f'NULL AS "{c}"' for c in FIELDS)
        clauses=[]; args=[]
        if start is not None: clauses.append('create_time >= ?');args.append(start)
        if end is not None: clauses.append('create_time < ?');args.append(end)
        if not full: clauses.append('(local_type & 4294967295) = 1')
        direction='DESC' if reverse else 'ASC'
        sql=f'SELECT {fields} FROM "{table}"'+ (' WHERE '+ ' AND '.join(clauses) if clauses else '')+f' ORDER BY create_time {direction}, local_id {direction}'
        names=data._name2id(con)
        for r in con.execute(sql,args):
            cancel();m=data._build_msg(r,names,uid,shard)
            ts=m['create_time'];sender=('Me' if m['is_sender'] else m['sender']) if m['sender_wxid'] else ('System' if m['kind']=='system' else 'Unknown sender')
            if m['kind']=='text' and not m['text'] and (r['message_content'] or r['compress_content']):
                raise ValueError('A text message could not be decoded. Export stopped to avoid silently losing text.')
            row=dict(timestamp=datetime.fromtimestamp(ts).astimezone().isoformat(sep=' ') if ts else '',sender=sender,sender_id=m['sender_wxid'],text=m['text'])
            if full:
                from content import describe
                row.update(describe(data,m,None))
            if keyword and keyword.casefold() not in (row['text']+' '+row['sender']).casefold():continue
            if full and media:row.update(describe(data,m,media))
            yield (ts,shard,m['local_id'] or 0),row
    streams=[shard_rows(i,c) for i,c in enumerate(data.msg_dbs)]
    interrupted=[]
    def sql_progress():
        try:cancel();return 0
        except Exception as e:interrupted.append(e);return 1
    try:
        for con in data.msg_dbs:con.set_progress_handler(sql_progress,1000)
        for _,row in heapq.merge(*streams,key=lambda v:v[0],reverse=reverse):yield row
    except sqlite3.OperationalError:
        if interrupted:raise interrupted[0]
        raise
    finally:
        for stream in streams:stream.close()
        for con in data.msg_dbs:con.set_progress_handler(None,0)

def messages(data, uid, start=None, end=None, limit=None, cancel=lambda:None, full=False, keyword="", media=None):
    from itertools import islice
    stream=iter_messages(data,uid,start,end,cancel,full,keyword,media,reverse=bool(limit))
    try:
        if limit:return list(reversed(list(islice(stream,limit))))
        return list(stream)
    finally:stream.close()
