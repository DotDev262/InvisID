
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from app.config import get_settings

settings = get_settings()

def encrypt_data(data: bytes) -> bytes:
    """
    Encrypt data using AES-256-GCM.
    Returns: IV (16 bytes) + Tag (16 bytes) + Ciphertext
    """
    # Use the first 32 bytes of MASTER_SECRET as the key
    key = settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return iv + tag + ciphertext

def decrypt_data(encrypted_content: bytes) -> bytes:
    """
    Decrypt data using AES-256-GCM.
    """
    key = settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')
    iv = encrypted_content[:16]
    tag = encrypted_content[16:32]
    ciphertext = encrypted_content[32:]
    
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    return cipher.decrypt_and_verify(ciphertext, tag)
