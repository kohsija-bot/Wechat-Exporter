"""Local media inventory. No account credentials, network, or database changes."""
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import os, shutil, tempfile, json, hashlib

IMAGE={'.jpg','.jpeg','.png','.gif','.webp','.bmp','.tif','.tiff','.heic','.heif','.avif','.ico'}
VIDEO={'.mp4','.mov','.m4v','.avi','.mkv','.webm','.3gp','.wmv','.mpeg','.mpg','.ts'}
CACHE={'.dat','.wxgf','.pic','.thumb','.t','.h','.hd','.media','.video','.image','.cache','.bin'}
SKIP={'.db','.sqlite','.sqlite3','.wal','.shm','.log','.ini','.json','.xml','.txt','.pdf','.docx','.xlsx','.zip','.exe','.dll'}
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
    def available(self):return self.status in ('Ready','Legacy image','V2 key supplied')

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

def inspect(path,base,keys=()):
    ext=path.suffix.lower();st=path.stat()
    if not st.st_size:return None
    with path.open('rb') as f:head=f.read(64)
    identified=signature(head);status='Ready';thumb=path.stem.lower().endswith(('_t','_thumb','_thumbnail','_preview')) or ext in ('.thumb','.t') or any(x.lower() in ('thumb','thumbnail','thumbnails') for x in path.parts)
    if identified:
        kind,extension=identified
        if kind=='Video' and ext in VIDEO:extension=ext
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
    def err(_):
        nonlocal errors;errors+=1
    for start in ([base/Path(x) for x in folders] if folders is not None else [base]):
        cancel()
        if not start.is_dir() or not start.resolve().is_relative_to(base):continue
        for directory,dirs,files in os.walk(start,followlinks=False,onerror=err):
            cancel();d=Path(directory)
            dirs[:]=[x for x in dirs if not (d/x).is_symlink() and not getattr(d/x,'is_junction',lambda:False)() and x.casefold() not in ('db_storage','logs','log') and not x.startswith(('Media_export_','.media-export-')) and (d/x).resolve().is_relative_to(base)]
            for name in files:
                cancel();count+=1
                if count%200==0:status(f'Scanning local files… {count:,} checked, {len(out):,} media found')
                p=d/name
                if p.suffix.lower() in SKIP:continue
                try:
                    if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(base) or p in seen:continue
                    seen.add(p);r=inspect(p,base,keys)
                    if r:out.append(r)
                except (OSError,ValueError,ImportError):errors+=1
    out.sort(key=lambda r:(-r.modified,r.relative.casefold()));return out,errors

def legacy_candidate(head):
    if not head or head.startswith((V1,V2)):return None
    for key in sorted({head[0]^x for x in (255,137,71,82)}):
        prefix=bytes(x^key for x in head)
        found=signature(prefix)
        if found and found[1] in ('.jpg','.png','.gif','.webp'):return key
    return None

def image_bytes(item,keys=(),cancel=lambda:None):
    p=Path(item.path)
    if p.stat().st_size>128*1024*1024:raise ValueError('Image exceeds 128 MiB safety limit')
    cancel();raw=p.read_bytes();cancel()
    if item.status=='Ready':blob=raw
    elif raw.startswith((V1,V2)):
        from wx4.offline_image import decode_dat
        blob=None
        for key in ([None] if raw.startswith(V1) else keys):
            cancel();candidate=decode_dat(raw,aes_key=key)
            if candidate and signature(candidate[:64]) and signature(candidate[:64])[0]=='Image':
                try:validate_raster(candidate);blob=candidate;break
                except ValueError:continue
    else:
        key=legacy_candidate(raw[:64]);blob=raw.translate(bytes(x^key for x in range(256))) if key is not None else None
    found=signature(blob[:64]) if blob else None
    if not found or found[0]!='Image':raise ValueError('Image could not be decoded. V2 may need the matching image key or an unsupported codec.')
    cancel();return blob,found[1]

def validate_raster(blob):
    # Verify decoded pixels, not merely a plausible file header.
    from PIL import Image
    import io
    try:
        with Image.open(io.BytesIO(blob)) as img:img.verify()
        with Image.open(io.BytesIO(blob)) as img:img.load()
    except Exception as exc:raise ValueError('Decoded image failed validation') from exc

def load_image_keys(path):
    # Import only an existing image-key file supplied explicitly by the user.
    # Do not save, log, or export key values.
    p=Path(path)
    if p.stat().st_size>65536:raise ValueError('Image key file is too large')
    raw=p.read_bytes()
    if len(raw)==16:return (raw,)
    try:
        value=json.loads(raw.decode('utf-8-sig'))
        values=value.get('keys',[]) if isinstance(value,dict) else []
    except (ValueError,UnicodeError):values=[raw.decode('ascii').strip()]
    keys=[]
    if not isinstance(values,list):raise ValueError('Invalid image key list')
    for v in values[:16]:
        if not isinstance(v,str):continue
        try:k=bytes.fromhex(v)
        except ValueError:continue
        if len(k)==16 and k not in keys:keys.append(k)
    if not keys:raise ValueError('No supported 16-byte image key in the supplied file')
    return tuple(keys)

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
                    blob,ext=image_bytes(item,keys,cancel);validate_raster(blob);dest=folder/(prefix+'_'+stem+ext);dest.write_bytes(blob)
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
