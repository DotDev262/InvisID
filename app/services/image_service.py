from imwatermark import WatermarkEncoder, WatermarkDecoder
import cv2

PAYLOAD_SIZE = 64

# simple XOR key
KEY = 23


def encrypt_employee_id(emp_id: str) -> str:
    """
    Encrypt employee ID using XOR cipher
    """
    encrypted = "".join(chr(ord(c) ^ KEY) for c in emp_id)
    return encrypted


def decrypt_employee_id(cipher: str) -> str:
    """
    Decrypt XOR cipher
    """
    decrypted = "".join(chr(ord(c) ^ KEY) for c in cipher)
    return decrypted


def embed_watermark(input_path: str, watermark_data: str, output_path: str) -> str:

    img = cv2.imread(input_path)

    if img is None:
        raise ValueError("Invalid image path")

    encoder = WatermarkEncoder()

    # encrypt employee id
    encrypted_id = encrypt_employee_id(watermark_data)

    print("EMPLOYEE ID:", watermark_data)
    print("ENCRYPTED WATERMARK:", encrypted_id)

    # repeat payload for robustness
    payload = (encrypted_id + "|") * 10
    payload = payload[:PAYLOAD_SIZE]

    encoder.set_watermark("bytes", payload.encode())

    watermarked = encoder.encode(img, "dwtDctSvd")

    print("WATERMARK EMBEDDED")

    cv2.imwrite(output_path, watermarked)

    return output_path


def extract_watermark(image_path: str) -> str:

    img = cv2.imread(image_path)

    if img is None:
        raise ValueError("Invalid image path")

    decoder = WatermarkDecoder("bytes", PAYLOAD_SIZE)

    watermark = decoder.decode(img, "dwtDctSvd")

    decoded = watermark.decode(errors="ignore")
    decoded = decoded.replace("\x00", "")

    print("RAW WATERMARK:", decoded)

    parts = decoded.split("|")
    parts = [p for p in parts if p.strip()]

    if not parts:
        print("NO WATERMARK FOUND")
        return ""

    # majority voting
    encrypted_id = max(set(parts), key=parts.count)

    print("EXTRACTED ENCRYPTED WATERMARK:", encrypted_id)

    try:
        employee_id = decrypt_employee_id(encrypted_id)
        print("DECRYPTED EMPLOYEE:", employee_id)
        return employee_id
    except Exception:
        print("DECRYPTION FAILED")
        return ""