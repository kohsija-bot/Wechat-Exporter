"""Local WeChat 4.x connection adapter for the current Windows user's own account.
Uses the supplied Moect GPLv3 reader/decryption modules. No key files or network.
"""
import os
import re
import sys
import tempfile
import shutil
from pathlib import Path

SQLITE_HEADER = b'SQLite format 3\0'

def wanted(name):
    return name in ('session.db','contact.db','message_resource.db') or bool(re.fullmatch(r'(?:(?:biz_)?message|media)_\d+\.db', name))

def detect(directory=None,cancel=lambda:None):
    if sys.platform != 'win32':
        raise RuntimeError('Live connection requires Windows 10/11 x64 and WeChat Desktop 4.x.')
    from wx4 import paths
    cancel()
    try:
        accounts=paths.selected_account_dirs(directory) if directory else paths.list_account_dirs()
    except ValueError as e:
        raise RuntimeError('No WeChat 4.x data folder found. Open WeChat Settings > File Management, then select the data folder.') from e
    if not accounts:
        raise RuntimeError('No local WeChat 4.x account found. Use Browse data folder to locate xwechat_files or db_storage.')
    cancel();return accounts

def make_snapshot(account, status=lambda _:None, cancel=lambda:None):
    """Return (snapshot directory, wxid, warning). Caller owns directory cleanup."""
    if sys.platform != 'win32':
        raise RuntimeError('Live connection requires Windows.')
    from wx4 import key, decrypt
    import psutil
    from reader import open_archive, sessions
    storage=Path(account['db_storage']).resolve()
    if not storage.is_dir() or storage.name!='db_storage':
        raise RuntimeError('Invalid account database folder.')
    source=[]
    for f in storage.rglob('*.db'):
        cancel()
        if wanted(f.name) and f.is_file() and f.stat().st_size:
            if not f.resolve().is_relative_to(storage):
                raise RuntimeError('Unexpected database path outside the selected account.')
            source.append(f)
    if not any(f.name=='session.db' for f in source) or not any('message_' in f.name for f in source):
        raise RuntimeError('Missing session or message database. Check WeChat data folder and sync history to desktop.')
    # Limit upstream process discovery to the current Windows user; do not request debug privilege.
    original_find=key.find_weixin_processes
    original_privilege=key.enable_debug_privilege
    username=psutil.Process().username().casefold()
    def own_processes():
        results=[]
        for p in original_find():
            try:
                if psutil.Process(p['pid']).username().casefold()==username:
                    results.append(p)
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                continue
        return results
    # Only the chat databases are needed; skip media and account-resource databases.
    class ChatExtractor(key.KeyExtractor):
        def collect(self):
            super().collect()
            self.db_files=[x for x in self.db_files if wanted(Path(x['rel']).name) and x['page1'][:16]!=SQLITE_HEADER]
            self.salt_index={}
            for x in self.db_files:self.salt_index.setdefault(x['salt'],[]).append(x)
            return self.db_files
    base=Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir()))/'WeChatExporter'/'temporary'
    base.mkdir(parents=True,exist_ok=True)
    dest=Path(tempfile.mkdtemp(prefix='snapshot-',dir=base))
    ex=None; keys={}
    try:
        key.find_weixin_processes=own_processes
        key.enable_debug_privilege=lambda:False
        if not own_processes():
            raise RuntimeError('WeChat 4.x is not running under your Windows account. Open and sign in to WeChat, then retry.')
        status('Reading local chat databases. This may take a while...')
        ex=ChatExtractor(str(storage),progress=lambda _:cancel(),cancel=cancel)
        ex.extract() # do not save database keys to disk
        keys={k:v for k,v in ex.result_payload().items() if not k.startswith('_')}
        cancel()
        status('Creating a temporary chat snapshot...')
        for f in source:
            cancel()
            with f.open('rb') as stream: plain=stream.read(16)==SQLITE_HEADER
            if plain:
                import sqlite3
                target=dest/f.relative_to(storage);target.parent.mkdir(parents=True,exist_ok=True)
                src=sqlite3.connect(f.resolve().as_uri()+'?mode=ro',uri=True)
                try:
                    dst=sqlite3.connect(target)
                    try:src.backup(dst,pages=128,progress=lambda *_:cancel())
                    finally:dst.close()
                finally:src.close()
        if keys:
            result=decrypt.decrypt_all(keys,str(storage),str(dest),progress=lambda _:status('Preparing chat snapshot...'),cancel=cancel)
            for rel,_ in result['failed']+result['skipped']:
                (dest/rel).unlink(missing_ok=True)
        missing=[f.name for f in source if not (dest/f.relative_to(storage)).is_file()]
        required=[x for x in missing if x=='session.db' or re.fullmatch(r'message_\d+\.db',x)]
        if required:
            raise RuntimeError('Cannot read all required chat databases: '+', '.join(required)+'. Check that the selected account is signed in and WeChat 4.x is compatible. Restart WeChat, open a conversation, then retry. No partial archive was opened.')
        if not any(dest.rglob('message_*.db')):
            raise RuntimeError('No readable chat database was recovered.')
        d=open_archive(dest,account.get('wxid',''),cancel=cancel)
        try:
            if not sessions(d,cancel):raise RuntimeError('No readable conversations in this desktop snapshot.')
        finally:d.close()
        if not any(dest.rglob('contact.db')) and 'contact.db' not in missing:missing.append('contact.db')
        warning=('Optional databases unavailable: '+', '.join(missing)+'. Some names or official-account messages may be missing.') if missing else ''
        return str(dest),account.get('wxid',''),warning
    except BaseException:
        shutil.rmtree(dest,ignore_errors=True);raise
    finally:
        keys.clear()
        if ex is not None:ex.keys.clear()
        key.find_weixin_processes=original_find
        key.enable_debug_privilege=original_privilege
