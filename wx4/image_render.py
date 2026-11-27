"""Local raster rendering. GPL-3.0; raster_payload adapted from Moect core/media_codec.py.
No key discovery, process inspection, or network requests.
"""
import io, os, re, shutil, subprocess, tempfile, time
from pathlib import Path
from PIL import Image

def raster_payload(blob):
    """Keep the complete raster, excluding cache metadata AFTER its end marker.

    JPEG APP/EXIF segments may themselves contain thumbnail end markers. Walk
    segments and entropy markers instead of taking the first/last FF D9 match.
    Decoder verification is still required after this structural boundary check.
    """
    size=len(blob)
    if blob.startswith(b'\xff\xd8'):
        pos=2;scan=False;saw_scan=False
        while pos<size:
            if scan:
                pos=blob.find(b'\xff',pos)
                if pos<0:return None
            elif blob[pos]!=0xff:return None
            while pos<size and blob[pos]==0xff:pos+=1
            if pos>=size:return None
            marker=blob[pos];pos+=1
            if scan and (marker==0 or 0xd0<=marker<=0xd7):continue
            if marker==0xd9:return blob[:pos] if saw_scan else None
            if marker in (0,0xd8) or 0xd0<=marker<=0xd7:return None
            if marker==1:continue
            if pos+2>size:return None
            length=int.from_bytes(blob[pos:pos+2],'big')
            if length<2 or pos+length>size:return None
            pos+=length;scan=marker==0xda or (scan and marker==0xdc)
            if scan:saw_scan=True
        return None
    if blob.startswith(b'\x89PNG\r\n\x1a\n'):
        pos=8
        while pos+12<=size:
            length=int.from_bytes(blob[pos:pos+4],'big');end=pos+12+length
            if end>size:return None
            if blob[pos+4:pos+8]==b'IEND':return blob[:end] if length==0 else None
            pos=end
        return None
    if blob.startswith(b'GIF8'):
        if size<13:return None
        pos=13+(3*(1<<((blob[10]&7)+1)) if blob[10]&128 else 0);frames=0
        while pos<size:
            marker=blob[pos];pos+=1
            if marker==0x3b:return blob[:pos] if frames else None
            if marker==0x21:
                if pos>=size:return None
                pos+=1  # Extension label; all extension payloads are subblocks.
            elif marker==0x2c:
                if pos+9>size:return None
                packed=blob[pos+8];pos+=9
                if packed&128:pos+=3*(1<<((packed&7)+1))
                pos+=1;frames+=1  # LZW minimum code size.
            else:return None
            while pos<size:
                length=blob[pos];pos+=1
                if not length:break
                pos+=length
            else:return None
        return None
    if blob.startswith(b'RIFF') and blob[8:12]==b'WEBP':
        end=int.from_bytes(blob[4:8],'little')+8
        return blob[:end] if 12<=end<=size else None
    return blob


def validate_image(blob):
    """Validate a complete raster, including actual pixel decoding."""
    try:
        with Image.open(io.BytesIO(blob)) as im:
            im.verify()
        with Image.open(io.BytesIO(blob)) as im:
            im.load()
    except Exception as exc:
        raise ValueError('Image data is invalid or unsupported by Pillow') from exc


def ffmpeg_path():
    # Use installed executable if present, otherwise imageio-ffmpeg's local binary.
    found=shutil.which('ffmpeg')
    if found:return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError,RuntimeError,OSError):
        raise ValueError('WXGF conversion needs FFmpeg; install imageio-ffmpeg or FFmpeg') from None


def wxgf_first_frame(blob, cancel=lambda:None):
    """Decode an already accessible WXGF HEVC payload into a PNG first frame.

    Not an original or animation export. Never invoke a shell or network protocol.
    """
    if not blob.startswith(b'wxgf'):raise ValueError('Not a WXGF image')
    cancel();starts=list(re.finditer(b'\x00\x00(?:\x00)?\x01',blob[4:])); units=[]
    for i,match in enumerate(starts):
        begin=4+match.end();end=4+starts[i+1].start() if i+1<len(starts) else len(blob)
        unit=blob[begin:end]
        if len(unit)>=2 and not unit[0]&128 and unit[1]&7:units.append(unit)
    vps=[i for i,u in enumerate(units) if (u[0]>>1)&63==32]
    groups=[]
    for i,begin in enumerate(vps):
        group=units[begin:vps[i+1] if i+1<len(vps) else len(units)]
        if any((u[0]>>1)&63<32 for u in group):groups.append(b''.join(b'\0\0\0\1'+u for u in group))
    candidates=sorted(groups,key=len,reverse=True)[:3]
    if units:candidates.append(b''.join(b'\0\0\0\1'+u for u in units))
    if not candidates:candidates=[blob[4:]]
    exe=ffmpeg_path();deadline=time.monotonic()+25
    with tempfile.TemporaryDirectory(prefix='wce-wxgf-') as tmp:
        src=Path(tmp)/'input.hevc';dst=Path(tmp)/'frame.png'
        for candidate in candidates:
            cancel();src.write_bytes(candidate);dst.unlink(missing_ok=True)
            if time.monotonic()>=deadline:break
            args=[exe,'-nostdin','-hide_banner','-loglevel','error','-xerror','-protocol_whitelist','file,pipe','-threads','1','-f','hevc','-i',str(src),'-map','0:v:0','-frames:v','1','-vf',"scale='min(4096,iw)':'min(4096,ih)':force_original_aspect_ratio=decrease",'-threads','1','-y',str(dst)]
            proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                while proc.poll() is None:
                    cancel()
                    if time.monotonic()>=deadline:break
                    time.sleep(.05)
                if proc.poll()==0 and dst.is_file() and dst.stat().st_size<=64*1024*1024:
                    data=dst.read_bytes();validate_image(data);return data
            finally:
                if proc.poll() is None:proc.kill()
                proc.wait()
    raise ValueError('WXGF HEVC first-frame conversion failed or timed out')


def render_image(blob,cancel=lambda:None):
    cancel()
    if blob.startswith(b'wxgf'):
        return wxgf_first_frame(blob,cancel),'.png','WXGF first frame (converted)'
    cleaned=raster_payload(blob)
    if cleaned is None:raise ValueError('Image has invalid or incomplete format boundaries')
    validate_image(cleaned)
    with Image.open(io.BytesIO(cleaned)) as im:
        ext={'JPEG':'.jpg','PNG':'.png','GIF':'.gif','WEBP':'.webp','BMP':'.bmp','TIFF':'.tiff','ICO':'.ico','AVIF':'.avif'}.get(im.format)
    if not ext:raise ValueError('Unsupported image format')
    cancel();return cleaned,ext,'Raster image'
