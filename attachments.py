"""Conservative local-only resource export. No network or new credential extraction."""
import hashlib,os,re,shutil
from pathlib import Path

IMAGE={'.jpg','.jpeg','.png','.gif','.webp','.bmp'}
VIDEO={'.mp4','.mov','.m4v','.avi','.mkv','.webm'}

def digest(path,cancel):
    h=hashlib.md5();
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):cancel();h.update(block)
    return h.hexdigest()

class LocalMedia:
    def __init__(self,account,output,cancel=lambda:None,image_keys=()):
        self.account=Path(account).resolve() if account else None;self.out=Path(output);self.cancel=cancel;self.index={};self.indexed=set();self.image_keys=image_keys
    def add_tree(self,base):
        if not self.account or not base.is_dir() or not base.resolve().is_relative_to(self.account) or base in self.indexed:return
        self.indexed.add(base)
        for root,dirs,files in os.walk(base,followlinks=False):
            self.cancel()
            for name in files:
                self.cancel();p=Path(root)/name
                if p.is_symlink() or not p.resolve().is_relative_to(self.account):continue
                self.index.setdefault(name.casefold(),set()).add(p);self.index.setdefault(p.stem.casefold(),set()).add(p)
    def reference_hashes(self,data,m):
        server=str(m.get('server_id') or '')
        if not server or server=='0':return set()
        from wx4.reader import reference_text
        out=set()
        for rel,con in data._conns.items():
            if not con or Path(rel).name!='message_resource.db':continue
            tables=data.tables_of(con)
            if not {'ChatName2Id','MessageResourceInfo'}<=tables:continue
            try:
                # Resource chat rowids are independent of message shard rowids.
                ids=[str(r[0]) for r in con.execute('SELECT rowid FROM ChatName2Id WHERE user_name=?',(m['session'],))]
                for chat in ids:
                    for row in con.execute('SELECT packed_info FROM MessageResourceInfo WHERE CAST(msg_svr_id AS TEXT)=? AND CAST(chat_name_id AS TEXT)=?',(server,chat)):
                        self.cancel();out.update(re.findall(r'(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])',reference_text(row[0]).lower()))
            except __import__('sqlite3').Error:continue
        return out
    def save(self,data,m):
        kind=m['kind']; result={'kind':kind,'status':'missing','reason':'No verified local resource found'}
        if kind=='voice':
            blob=data.voice_blob(m.get('session',''),m.get('server_id','')) if not m.get('_forward_item') else None
            if blob:
                ext='.silk' if blob.startswith((b'#!SILK',b'\x02#!SILK')) else '.bin'
                dest=self.out/'media'/('voice_'+hashlib.sha256(blob).hexdigest()[:24]+ext);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob)
                return {'kind':kind,'status':'saved_raw','path':dest.relative_to(self.out).as_posix(),'reason':'Original audio; external decoder may be required'}
            return result
        if not self.account:return result
        hints=m.get('_media') or {}; hashes={h.lower() for h in hints.get('main_hashes',[]) if re.fullmatch('[0-9a-fA-F]{32}',h)}
        if kind in ('image','emoji','video') and not m.get('_forward_item'):
            # Packed message metadata contains resource hashes even when XML has none.
            # A candidate still has to match its decoded or original content MD5.
            hashes.update(re.findall(r'(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])',m.get('_resource_source','').lower()))
            hashes.update(self.reference_hashes(data,m))
        if not hashes:return {**result,'reason':'No verifiable content hash in message or resource metadata'}
        self.add_tree(self.account/'msg'/'attach'/data.msg_table_for(m['session'])[4:])
        for sub in ('file','video','emoji','emotion','emoticon','record','recorditem'):
            self.add_tree(self.account/'msg'/sub)
        for sub in ('cache','emotion','business/emoticon','FileStorage/CustomEmotion'):
            self.add_tree(self.account/sub)
        candidates=set()
        for h in hashes:
            for key in (h,h+'_h',h+'_hd',h+'.h',h+'.hd',h+'_t',h+'_thumb'):candidates.update(self.index.get(key,set()))
        for value in list(hints.get('paths',[]))+[m.get('extra',{}).get('filename','')]:
            if value:candidates.update(self.index.get(str(value).replace('\\','/').split('/')[-1].casefold(),set()))
        encrypted=False
        for path in sorted(candidates):
            self.cancel();ext=path.suffix.lower()
            if kind in ('image','emoji') and ext not in IMAGE:
                encrypted=True
                try:
                    if path.stat().st_size>64*1024*1024:continue
                    from wx4.offline_image import decode_dat
                    from wx4.image_render import render_image,raster_payload
                    raw=path.read_bytes();self.cancel();blob=decode_dat(raw)
                    if not blob:
                        for key in self.image_keys:
                            self.cancel();blob=decode_dat(raw,aes_key=key,xor_key=getattr(self.image_keys,'xor',None))
                            if blob and (hashlib.md5(blob).hexdigest() in hashes or hashlib.md5(raster_payload(blob) or b'').hexdigest() in hashes):break
                            blob=None
                    if not blob or (hashlib.md5(blob).hexdigest() not in hashes and hashlib.md5(raster_payload(blob) or b'').hexdigest() not in hashes):continue
                    blob,extension,quality=render_image(blob,self.cancel)
                    dest=self.out/'media'/ (hashlib.sha256(blob).hexdigest()[:24]+extension);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob)
                    return {'kind':kind,'status':'saved','path':dest.relative_to(self.out).as_posix(),'quality':quality}
                except (OSError,ImportError,ValueError):continue
            if ext in ('.dat','.wxgf','.pic'):encrypted=True;continue
            if kind in ('image','emoji') and ext not in IMAGE:continue
            if kind=='video':
                from media_catalog import signature
                try:
                    with path.open('rb') as f: identified=signature(f.read(64))
                except OSError:continue
                if not identified or identified[0]!='Video':continue
            try:
                if digest(path,self.cancel) not in hashes:continue
                dest=self.out/'media'/ (hashlib.sha256(str(path).encode()).hexdigest()[:16]+'_'+re.sub(r'[^\w. -]','_',path.name)[:100]);dest.parent.mkdir(parents=True,exist_ok=True)
                if kind=='video' and ext not in VIDEO:dest=dest.with_suffix(identified[1])
                with path.open('rb') as src,dest.open('wb') as dst:
                    for block in iter(lambda:src.read(1024*1024),b''):self.cancel();dst.write(block)
                if digest(dest,self.cancel) not in hashes:dest.unlink();continue
                return {'kind':kind,'status':'saved','path':dest.relative_to(self.out).as_posix()}
            except OSError:continue
        return {**result,'status':'encrypted_or_unsupported' if encrypted else 'missing','reason':'Encrypted cache or original file unavailable' if encrypted else result['reason']}
