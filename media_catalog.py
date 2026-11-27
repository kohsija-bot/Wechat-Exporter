"""Local media inventory. No account credentials, network, or database changes."""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from datetime import datetime
import os, shutil, tempfile, json, hashlib

IMAGE={'.jpg','.jpeg','.png','.gif','.webp','.bmp','.tif','.tiff','.heic','.heif','.avif','.ico'}
VIDEO={'.mp4','.mov','.m4v','.avi','.mkv','.webm','.3gp','.wmv','.mpeg','.mpg','.ts'}
CACHE={'.dat','.wxgf','.pic','.thumb','.t','.h','.hd','.media','.video','.image','.cache','.bin'}
SKIP={'.db','.sqlite','.sqlite3','.wal','.shm','.log','.ini','.json','.xml','.txt','.pdf','.docx','.xlsx','.zip','.exe','.dll'}
ACCOUNT_MEDIA_FOLDERS=('msg/attach','msg/video','msg/image','msg/emoji','msg/emotion','msg/emoticon','msg/record','msg/recorditem','cache','emotion','business/emoticon','FileStorage/MsgAttach','FileStorage/Image','FileStorage/Video','FileStorage/CustomEmotion')

V1=b'\x07\x08V1\x08\x07'
V2=b'\x07\x08V2\x08\x07'
@dataclass(frozen=True)
class Media:
    path: str
    relative: str
    kind: str
    extension: str
    status: str
    size: int
    modified: float
    thumbnail: bool=False
    @property
    def available(self):return self.status in ('Ready','Legacy image','V2 key supplied','WXGF image')

def signature(head):
    if head.startswith(b'\xff\xd8\xff'):return 'Image','.jpg'
    if head.startswith(b'\x89PNG\r\n\x1a\n'):return 'Image','.png'
    if head.startswith((b'GIF87a',b'GIF89a')):return 'Image','.gif'
    if head.startswith(b'RIFF') and head[8:12]==b'WEBP':return 'Image','.webp'
    if head.startswith(b'BM'):return 'Image','.bmp'
    if head.startswith((b'II*\0',b'MM\0*')):return 'Image','.tiff'
    if len(head)>=12 and head[4:8]==b'ftyp':
        if head[8:12] in (b'heic',b'heix',b'hevc',b'hevx',b'mif1',b'msf1'):return 'Image','.heic'
        if head[8:12] in (b'avif',b'avis'):return 'Image','.avif'
        return 'Video','.mp4'
    if head.startswith(b'RIFF') and head[8:12]==b'AVI ':return 'Video','.avi'
    if head.startswith(b'\x1a\x45\xdf\xa3'):return 'Video','.mkv'
    if len(head)>=8 and head[4:8] in (b'moov',b'mdat',b'wide'):return 'Video','.mov'
    if head.startswith(b'\x00\x00\x01\xba'):return 'Video','.mpg'
    if head.startswith(bytes.fromhex('3026b2758e66cf11a6d900aa0062ce6c')):return 'Video','.wmv'
    if head.startswith(b'\x00\x00\x01\x00'):return 'Video','.mpg'
    return None

def inspect(path,base,keys=(),st=None):
    ext=path.suffix.lower();st=st if st is not None else path.stat()
    if not st.st_size:return None
    with path.open('rb') as f:head=f.read(64)
    identified=signature(head);status='Ready';thumb=path.stem.lower().endswith(('_t','_thumb','_thumbnail','_preview')) or ext in ('.thumb','.t') or any(x.lower() in ('thumb','thumbnail','thumbnails') for x in path.parts)
    if identified:
        kind,extension=identified
        if kind=='Video' and ext in VIDEO:extension=ext
    elif head.startswith(b'wxgf'):
        kind,extension,status='Image','.wxgf','WXGF image'
    elif head.startswith(V2):
        kind,extension,status='Image','.dat','V2 key supplied' if keys else 'Encrypted V2 image'
    elif head.startswith(V1) or (ext not in IMAGE|VIDEO and legacy_candidate(head) is not None):
        kind,extension,status='Image','.dat','Legacy image'
    elif ext in ('.dat','.wxgf','.pic','.thumb','.t','.h','.hd'):
        kind,extension='Image',ext;status='Locked / unsupported'
    elif ext in IMAGE:kind,extension='Image',ext;status='Unverified format'
    elif ext in VIDEO:kind,extension='Video',ext;status='Unverified format'
    else:return None
    return Media(str(path),path.relative_to(base).as_posix(),kind,extension,status,st.st_size,st.st_mtime,thumb)

def scan(root, folders=None, cancel=lambda:None, status=lambda _:None, keys=()):
    base=Path(root).resolve(strict=True);out=[];errors=0;seen=set();count=0
    if not base.is_dir():raise ValueError('Choose an existing local media folder.')
    for start in ([base/Path(x) for x in folders] if folders is not None else [base]):
        cancel()
        try:
            if not start.is_dir() or not start.resolve().is_relative_to(base):continue
            # Do not enter a symlink/junction even if it points inside the account.
            if any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (start,*start.parents) if p!=base and p.is_relative_to(base)):continue
        except OSError:errors+=1;continue
        pending=[start]
        status(f'Scanning {start.relative_to(base).as_posix()}…')
        while pending:
            cancel();directory=pending.pop()
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        cancel();count+=1
                        if count%200==0:status(f'Scanning local files… {count:,} checked, {len(out):,} media found')
                        try:
                            if entry.is_symlink() or getattr(entry,'is_junction',lambda:False)():continue
                            if entry.is_dir(follow_symlinks=False):
                                if entry.name.casefold() not in ('db_storage','logs','log','.venv') and not entry.name.startswith(('Media_export_','.media-export-')):pending.append(Path(entry.path))
                                continue
                            if not entry.is_file(follow_symlinks=False):continue
                            p=Path(entry.path)
                            if p.suffix.lower() in SKIP or p in seen:continue
                            seen.add(p);r=inspect(p,base,keys,entry.stat(follow_symlinks=False))
                            if r:out.append(r)
                        except (OSError,ValueError,ImportError):errors+=1
            except OSError:errors+=1
    cancel()
    out.sort(key=lambda r:(-r.modified,r.relative.casefold()));return out,errors

def legacy_candidate(head):
    if not head or head.startswith((V1,V2)):return None
    for key in sorted({head[0]^x for x in (255,137,71,82)}):
        prefix=bytes(x^key for x in head)
        found=signature(prefix)
        if found and found[1] in ('.jpg','.png','.gif','.webp'):return key
    return None

class ImageKeys(tuple):
    """Existing user-supplied keys only; retain the optional independent XOR byte."""
    def __new__(cls,keys=(),xor=None):
        obj=super().__new__(cls,keys);obj.xor=xor;return obj

def with_keys(item,keys):
    if item.status in ('Encrypted V2 image','V2 key supplied'):
        return replace(item,status='V2 key supplied' if keys else 'Encrypted V2 image')
    return item

def image_result(item,keys=(),cancel=lambda:None):
    from wx4.image_render import render_image
    p=Path(item.path)
    if p.stat().st_size>128*1024*1024:raise ValueError('Image exceeds 128 MiB safety limit')
    cancel();raw=p.read_bytes();cancel()
    if raw.startswith(V2) and not keys:raise ValueError('Image access is not available for this account. Save the picture in WeChat, or use existing image access.')
    if raw.startswith((V1,V2)):
        from wx4.offline_image import decode_dat
        failure=None
        for key in ([None] if raw.startswith(V1) else keys):
            cancel();candidate=decode_dat(raw,aes_key=key,xor_key=getattr(keys,'xor',None))
            if candidate:
                try:
                    return render_image(candidate,cancel)
                except ValueError as exc:failure=exc
        if failure is not None:raise failure
        raise ValueError('Image access does not match, image data is incomplete, or format conversion failed.')
    if item.status in ('Ready','WXGF image'):candidate=raw
    else:
        key=legacy_candidate(raw[:64]);candidate=raw.translate(bytes(x^key for x in range(256))) if key is not None else None
    if not candidate:raise ValueError('Unsupported or damaged local image')
    return render_image(candidate,cancel)

def image_bytes(item,keys=(),cancel=lambda:None):
    blob,ext,_=image_result(item,keys,cancel);return blob,ext

def validate_raster(blob):
    from wx4.image_render import validate_image
    validate_image(blob)

def load_image_keys(path):
    # Import only an existing image-key file supplied explicitly by the user.
    # Do not save, log, or export key values.
    p=Path(path)
    if p.stat().st_size>65536:raise ValueError('Image key file is too large')
    raw=p.read_bytes()
    if len(raw)==16:return ImageKeys((raw,))
    xor=None
    try:
        value=json.loads(raw.decode('utf-8-sig'))
        values=value.get('keys',[]) if isinstance(value,dict) else []
        if isinstance(value,dict) and value.get('xor') is not None:
            xor=value['xor']
    except (ValueError,UnicodeError):values=[raw.decode('ascii').strip()]
    if xor is not None and (type(xor) is not int or not 0<=xor<=255):raise ValueError('Invalid XOR byte in image key file')
    keys=[]
    if not isinstance(values,list):raise ValueError('Invalid image key list')
    for v in values[:16]:
        if not isinstance(v,str):continue
        try:k=bytes.fromhex(v)
        except ValueError:continue
        if len(k)==16 and k not in keys:keys.append(k)
    if not keys:raise ValueError('No supported 16-byte image key in the supplied file')
    return ImageKeys(keys,xor)

def existing_account_image_keys(account, wxid, cancel=lambda:None, localappdata=None):
    """Reuse only an existing Moect image-key cache for this exact account.

    No process access, broad searches, new key recovery, or writing key files.
    A cache hit is not proof that any specific image can be decoded.
    """
    local = localappdata or os.environ.get('LOCALAPPDATA')
    if not local or not account or not wxid:
        return ImageKeys()
    identity = hashlib.sha256((str(Path(account).resolve())+'\0'+wxid).encode()).hexdigest()
    for app in ('Moect','WeChatExporter'):
        cancel()
        root = Path(local)/app
        # The upstream default cache root. Custom storage stays an explicit import.
        path = root/'media-cache'/identity/'image-keys.json'
        try:
            if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve()):
                return load_image_keys(path)
        except (OSError, ValueError, UnicodeError, RuntimeError):
            continue
    return ImageKeys()

def export(items,output,cancel=lambda:None,progress=lambda *_:None,status=lambda _:None,keys=()):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.media-export-',dir=output));target=None;report=[];saved=0
    try:
        for i,item in enumerate(items,1):
            cancel();status(f'Exporting {i:,}/{len(items):,}');entry=asdict(item);entry.pop('path');dest=None
            try:
                if not item.available and not (item.status=='Encrypted V2 image' and keys):raise ValueError(item.status)
                p=Path(item.path);st=p.stat()
                if p.is_symlink() or st.st_size!=item.size or st.st_mtime!=item.modified:raise ValueError('Source changed; refresh and retry')
                folder=stage/('Images' if item.kind=='Image' else 'Videos');folder.mkdir(exist_ok=True)
                stem=p.stem[:80].rstrip(' .') or 'media';prefix=hashlib.sha256(item.relative.encode('utf-8')).hexdigest()[:12];ext=item.extension
                if item.kind=='Image' and item.status!='Ready':
                    blob,ext,quality=image_result(item,keys,cancel);dest=folder/(prefix+'_'+stem+ext);dest.write_bytes(blob);entry['quality']=quality
                else:
                    dest=folder/(prefix+'_'+stem+ext)
                    with p.open('rb') as src,dest.open('xb') as dst:
                        for block in iter(lambda:src.read(1024*1024),b''):cancel();dst.write(block)
                    if dest.stat().st_size!=item.size:raise ValueError('Incomplete copy')
                new=p.stat()
                if new.st_size!=st.st_size or new.st_mtime!=st.st_mtime:raise ValueError('Source changed while copying; refresh and retry')
                entry.update(result='saved',output=dest.relative_to(stage).as_posix());saved+=1
            except (OSError,ValueError,ImportError) as e:
                if dest:dest.unlink(missing_ok=True)
                entry.update(result='skipped',reason=str(e))
            report.append(entry);progress(i,len(items))
        cancel();(stage/'manifest.json').write_text(json.dumps({'requested':len(items),'saved':saved,'skipped':len(items)-saved,'files':report},ensure_ascii=False,indent=2),encoding='utf-8')
        base='Media_export_'+datetime.now().strftime('%Y%m%d-%H%M%S')
        for i in range(10000):
            candidate=output/(base+(f'_{i}' if i else ''))
            try:candidate.mkdir();target=candidate;break
            except FileExistsError:continue
        if target is None:raise ValueError('Unable to reserve a new output folder')
        try:os.replace(stage,target) if os.name!='nt' else _publish_windows(stage,target)
        except BaseException:shutil.rmtree(target,ignore_errors=True);raise
        return str(target),saved,len(items)-saved
    finally:shutil.rmtree(stage,ignore_errors=True)

def _publish_windows(stage,target):
    # Windows cannot replace an existing directory, even when empty.
    # Move into the reserved folder; caller removes it if publication fails.
    for p in stage.iterdir():shutil.move(str(p),str(target/p.name))
