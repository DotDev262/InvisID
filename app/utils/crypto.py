
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from app.config import get_settings

settings = get_settings()

def _derive_key(salt: bytes = b"invisid_storage") -> bytes:
    """Derive encryption key using PBKDF2."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        settings.MASTER_SECRET.encode(),
        salt,
        iterations=100000,
        dklen=32
    )

def encrypt_data(data: bytes) -> bytes:
    """
    Encrypt data using AES-256-GCM with derived key.
    Returns: IV (12 bytes) + Tag (16 bytes) + Ciphertext
    """
    key = _derive_key()
    iv = get_random_bytes(12)  # GCM recommended IV size
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return iv + tag + ciphertext

def decrypt_data(encrypted_content: bytes) -> bytes:
    """
    Decrypt data using AES-256-GCM with backward compatibility.
    Tries new PBKDF2 method first, then falls back to legacy method.
    """
    if len(encrypted_content) < 28:
        raise ValueError("Invalid encrypted data")
    
    # Try new PBKDF2 method (12-byte IV)
    if len(encrypted_content) >= 28:
        try:
            key = _derive_key()
            iv = encrypted_content[:12]
            tag = encrypted_content[12:28]
            ciphertext = encrypted_content[28:]
            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
            return cipher.decrypt_and_verify(ciphertext, tag)
        except Exception:
            pass
    
    # Fallback to legacy method (16-byte IV, direct key)
    try:
        key = settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')
        iv = encrypted_content[:16]
        tag = encrypted_content[16:32]
        ciphertext = encrypted_content[32:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, tag)
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")
