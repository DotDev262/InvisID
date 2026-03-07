import base64
import json
import time
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


class CryptoService:
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        self.key = key

    def encrypt(self, employee_id: str, image_id: str) -> str:
        """
        Encrypt employee information before embedding in image watermark
        """

        payload = {
            "employee_id": employee_id,
            "image_id": image_id,
            "issued_at": int(time.time())
        }

        plaintext = json.dumps(payload).encode()

        nonce = get_random_bytes(12)

        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)

        ciphertext, tag = cipher.encrypt_and_digest(plaintext)

        token = nonce + ciphertext + tag

        return base64.urlsafe_b64encode(token).decode()

    def decrypt(self, token: str) -> dict:
        """
        Decrypt extracted watermark
        """

        raw = base64.urlsafe_b64decode(token)

        nonce = raw[:12]
        tag = raw[-16:]
        ciphertext = raw[12:-16]

        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)

        plaintext = cipher.decrypt_and_verify(ciphertext, tag)

        return json.loads(plaintext.decode())
