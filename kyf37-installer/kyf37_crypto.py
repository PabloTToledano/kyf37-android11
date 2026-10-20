"""Per-user signing for a stock KYF37: key, keystore and signed boot/recovery images.

Generalised from the project's own signing scripts (device-inspection/sign-owner-recovery.py, sign-rom-boot.py,
prepare-recovery-signing.py). The bootloader is locked and only boots images signed with a key listed in its
keystore partition. The OEM key is read out of the phone's own aboot; the keystore is rewritten to hold the
user's public key in its place, with the same length and structure. The private key is created on this computer,
never printed and never leaves the workspace folder."""
import hashlib, os, struct
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

PARTITION_BYTES = 16 * 1024 * 1024
KEYSTORE_BYTES = 512 * 1024
# Where this bootloader keeps its OEM keystore (from its read_oem_keystore() MOVW/MOVT), inside aboot.img.
OEM_KEYSTORE_OFFSET = 0x8000 + 0x8f6447bc - 0x8f600000


class SigningError(Exception):
    pass


def read_tlv(b, pos=0):
    start = pos
    tag = b[pos]; pos += 1
    n = b[pos]; pos += 1
    if n & 128:
        count = n & 127
        if not 0 < count <= 4:
            raise SigningError('bad DER length')
        n = int.from_bytes(b[pos:pos + count], 'big'); pos += count
    end = pos + n
    if end > len(b):
        raise SigningError('DER item runs past the end of the data')
    return tag, b[pos:end], b[start:end], end


def children(b):
    out, pos = [], 0
    while pos < len(b):
        item = read_tlv(b, pos); out.append(item); pos = item[3]
    return out


def tlv(tag, data):
    n = len(data)
    length = bytes([n]) if n < 128 else bytes([128 + (n.bit_length() + 7) // 8]) + n.to_bytes((n.bit_length() + 7) // 8, 'big')
    return bytes([tag]) + length + data


def seq(*items):
    return tlv(0x30, b''.join(items))


def integer(n):
    b = n.to_bytes(max(1, (n.bit_length() + 7) // 8), 'big')
    if b[0] & 128:
        b = b'\0' + b
    return tlv(2, b)


def boot_body_end(data):
    """Offset where the Android boot image payload ends and the vendor signature envelope starts."""
    if data[:8] != b'ANDROID!':
        raise SigningError('not an Android boot image')
    f = struct.unpack_from('<10I', data, 8); page = f[7]
    if page not in (2048, 4096, 8192, 16384):
        raise SigningError('unexpected page size')
    end = page + sum((n + page - 1) // page * page for n in (f[0], f[2], f[4], f[8]))
    if end > len(data):
        raise SigningError('boot image shorter than its header says')
    return end


def stock_oem_keystore(aboot):
    """The OEM keystore DER and its parts. Refuses to continue unless the structure is exactly what was verified."""
    try:
        tag, payload, oem, _ = read_tlv(aboot, OEM_KEYSTORE_OFFSET)
        ks = children(payload); keybag = children(ks[1][1]); key = children(keybag[0][1])
        if tag != 0x30 or len(ks) != 3 or len(key) != 2:
            raise SigningError('keystore layout differs')
        public = serialization.load_der_public_key(key[1][2])
    except (IndexError, ValueError, SigningError) as e:
        raise SigningError('This phone\'s aboot does not hold the OEM keystore where the verified KYF37 build keeps it '
                           f'({e}). Stop: this stock build is not supported by this installer.')
    return oem, ks, key, public


def verify_stock_boot(boot, public):
    """The stock boot must verify against the OEM key from aboot: proves we found the right key and the right image."""
    end = boot_body_end(boot)
    tag, value, _, _ = read_tlv(boot, end)
    sig = children(value)
    if tag != 0x30 or len(sig) not in (4, 5) or sig[-1][0] != 4:
        raise SigningError('stock boot signature envelope has an unexpected shape')
    public.verify(sig[-1][1], boot[:end] + sig[-2][2], padding.PKCS1v15(), hashes.SHA256())
    return True


def load_or_create_key(path):
    path = Path(path)
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return key


def build_keystore(aboot, stock_keystore, private):
    """Keystore partition image with the user's public key in place of the OEM key (same length, same layout)."""
    oem, ks, key, _ = stock_oem_keystore(aboot)
    public_der = private.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.PKCS1)
    new = seq(ks[0][2], seq(seq(key[0][2], public_der)), ks[2][2])
    if len(new) != len(oem):
        raise SigningError('new keystore length differs from the OEM keystore')
    if len(stock_keystore) != KEYSTORE_BYTES:
        raise SigningError('keystore partition is not 512 KiB')
    return new + stock_keystore[len(new):]


def sign_image(source, template, target, private):
    """Sign a boot/recovery image body (any previous envelope is dropped) in the vendor's exact envelope.
    `template` is the stock image of the same kind: its version/certificate/algorithm fields are reused."""
    end = boot_body_end(source)
    tend = boot_body_end(template)
    fields = children(read_tlv(template, tend)[1])
    if len(fields) != 5:
        raise SigningError('template signature envelope has an unexpected shape')
    attr = seq(tlv(0x13, target), integer(end))
    signature = private.sign(source[:end] + attr, padding.PKCS1v15(), hashes.SHA256())
    out = source[:end] + seq(fields[0][2], fields[1][2], fields[2][2], attr, tlv(4, signature))
    if len(out) > PARTITION_BYTES:
        raise SigningError('signed image does not fit the 16 MiB partition')
    out += bytes(PARTITION_BYTES - len(out))
    private.public_key().verify(signature, out[:end] + attr, padding.PKCS1v15(), hashes.SHA256())
    if out[:end] != source[:end]:
        raise SigningError('image body changed while signing')
    return out


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def md5(data):
    return hashlib.md5(data).hexdigest()
