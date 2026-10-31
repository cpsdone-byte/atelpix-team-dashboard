"""Offline security primitives for Atelpix Secure Client Dashboard."""
from __future__ import annotations
import base64, hashlib, hmac, os, secrets, struct, time
from pathlib import Path
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DB_MAGIC = b'ATELPIXDB1'  # versioned encrypted database container
BACKUP_MAGIC = b'ATELPIXBA1'
SALT_LEN, NONCE_LEN = 16, 12
TIME_COST, MEMORY_COST, PARALLELISM = 3, 65536, 2

class SecurityError(Exception): pass


def derive_key(password: str, salt: bytes) -> bytes:
    if not isinstance(password, str) or len(password) < 12:
        raise SecurityError('Password must contain at least 12 characters.')
    return hash_secret_raw(password.encode('utf-8'), salt, TIME_COST, MEMORY_COST, PARALLELISM, 32, Type.ID)


def encrypt_container(magic: bytes, plaintext: bytes, password: str) -> bytes:
    salt, nonce = os.urandom(SALT_LEN), os.urandom(NONCE_LEN)
    key = derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, magic + salt)
    return magic + salt + nonce + ciphertext


def decrypt_container(magic: bytes, blob: bytes, password: str) -> bytes:
    head = len(magic)
    if len(blob) < head + SALT_LEN + NONCE_LEN + 16 or not blob.startswith(magic):
        raise SecurityError('Invalid or damaged encrypted file.')
    salt = blob[head:head+SALT_LEN]
    nonce = blob[head+SALT_LEN:head+SALT_LEN+NONCE_LEN]
    ciphertext = blob[head+SALT_LEN+NONCE_LEN:]
    try:
        return AESGCM(derive_key(password, salt)).decrypt(nonce, ciphertext, magic + salt)
    except Exception as exc:
        raise SecurityError('Incorrect password or file integrity check failed.') from exc


def totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode('ascii').rstrip('=')


def totp_code(secret: str, for_time: int | None = None, step: int = 30) -> str:
    counter = int((time.time() if for_time is None else for_time) // step)
    key = base64.b32decode(secret + '=' * ((8 - len(secret) % 8) % 8))
    digest = hmac.new(key, struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack('>I', digest[offset:offset+4])[0] & 0x7fffffff) % 1000000
    return f'{number:06d}'


def verify_totp(secret: str, code: str, at_time: int | None = None, window: int = 1) -> bool:
    if not (isinstance(code, str) and code.isdigit() and len(code) == 6): return False
    now = int(time.time() if at_time is None else at_time)
    return any(hmac.compare_digest(totp_code(secret, now + delta * 30), code) for delta in range(-window, window+1))


def make_recovery_codes(count: int = 10) -> list[str]:
    return ['-'.join([secrets.token_hex(2).upper(), secrets.token_hex(2).upper(), secrets.token_hex(2).upper()]) for _ in range(count)]


def recovery_hash(code: str) -> str:
    normalized = ''.join(c for c in code.upper() if c.isalnum())
    return hashlib.sha256(normalized.encode()).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with open(temp, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)
    try:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x2)  # hidden
    except Exception: pass
