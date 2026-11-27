"""Offline image decoding extracted from Moect wx4/media.py (GPL-3.0).
Only legacy XOR and fixed V1 formats; does not retrieve account-specific image keys.
"""
import hashlib,struct
from Cryptodome.Cipher import AES
SIG_V1 = bytes.fromhex("070856310807")
SIG_V2 = bytes.fromhex("070856320807")
V1_KEY = hashlib.md5(b"0").hexdigest()[:16].encode()

IMG_EXT = ((b"\xff\xd8\xff", ".jpg"), (b"\x89PNG", ".png"), (b"GIF8", ".gif"),
           (b"RIFF", ".webp"), (b"BM", ".bmp"), (b"wxgf", ".wxgf"))

def sniff_ext(data: bytes) -> str:
    for magic, ext in IMG_EXT:
        if data.startswith(magic):
            return ext
    return ".bin"


def _pkcs7_strip(data: bytes) -> bytes | None:
    if data and 1 <= data[-1] <= 16 and data[-data[-1]:] == bytes([data[-1]]) * data[-1]:
        return data[:-data[-1]]
    return None


def dat_layout(data: bytes):
    """V4 has a 15-byte header and a PKCS#7 padded AES prefix.

    Byte 14 is a flag, not the separately stored account XOR key. A full
    padding block is present even when aes_size is already divisible by 16.
    """
    if len(data)<31 or data[:6] not in (SIG_V1,SIG_V2):return None
    aes_size,xor_size=struct.unpack_from('<LL',data,6)
    aligned=(aes_size//16+1)*16
    end=15+aligned
    tail=len(data)-xor_size
    if aes_size<=0 or end>len(data) or tail<end:return None
    return data[15:end],data[end:tail],data[tail:],data[14]


def image_prefix(data):
    if data.startswith((b'\xff\xd8\xff',b'\x89PNG\r\n\x1a\n',b'GIF8',b'BM',b'wxgf')):return True
    return data.startswith(b'RIFF') and data[8:12]==b'WEBP'


def decrypt_dat_prefix(data, key):
    """Validate a key with the COMPLETE AES segment, padding and declared size.

    A two-byte BMP signature alone produces frequent false positives during a
    process scan. It must never be sufficient to accept or cache an AES key.
    """
    lay=dat_layout(data)
    if not lay or not key or len(key)!=16:return None
    try:plain=_pkcs7_strip(AES.new(key,AES.MODE_ECB).decrypt(lay[0]))
    except ValueError:return None
    if plain is None or len(plain)!=struct.unpack_from('<L',data,6)[0]:return None
    return plain if image_prefix(plain) else None


def infer_xor_key(data, prefix=b''):
    lay=dat_layout(data)
    if not lay or not lay[2]:return None
    tail=lay[2]
    endings=[]
    if prefix.startswith(b'\xff\xd8'):endings=[b'\xff\xd9']
    elif prefix.startswith(b'\x89PNG'):endings=[b'IEND\xaeB`\x82']
    for ending in endings:
        if len(tail)<len(ending):continue
        keys={a^b for a,b in zip(tail[-len(ending):],ending)}
        if len(keys)==1:return keys.pop()
    return None


def decode_dat(data: bytes, aes_key: bytes | None=None, xor_key: int | None=None):
    if image_prefix(data):return data
    if data[:6] not in (SIG_V1,SIG_V2):
        if not data:return None
        # Each supported signature fixes the XOR byte from the first byte.
        # Keep numeric order for legacy files that match more than one prefix.
        for k in sorted({data[0]^magic[0] for magic,_ in IMG_EXT}):
            if image_prefix(bytes(b^k for b in data[:16])):
                return data.translate(bytes(value^k for value in range(256)))
        return None
    key=V1_KEY if data[:6]==SIG_V1 else aes_key
    if not key or len(key)!=16:return None
    lay=dat_layout(data)
    if not lay:return None
    _aes_ct,mid,xor_ct,_flag=lay
    prefix=decrypt_dat_prefix(data,key)
    if prefix is None:return None
    if xor_ct:
        xk=xor_key if xor_key is not None else infer_xor_key(data,prefix)
        if xk is None:return None
        return prefix+mid+bytes(b^(xk&255) for b in xor_ct)
    return prefix+mid


