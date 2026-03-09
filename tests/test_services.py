import pytest
from app.utils.crypto import encrypt_data, decrypt_data
from app.services.image_service import encrypt_employee_id, decrypt_employee_id

def test_crypto_encryption_decryption():
    original_data = b"secure_forensic_data_12345"
    
    # Encrypt
    encrypted = encrypt_data(original_data)
    assert encrypted != original_data
    assert len(encrypted) > len(original_data)  # Includes IV and Tag
    
    # Decrypt
    decrypted = decrypt_data(encrypted)
    assert decrypted == original_data

def test_watermark_id_encryption():
    emp_id = "EMP-001"
    
    # Encrypt
    cipher = encrypt_employee_id(emp_id)
    assert cipher != emp_id
    
    # Decrypt
    decrypted = decrypt_employee_id(cipher)
    assert decrypted == emp_id

def test_watermark_id_encryption_special_chars():
    emp_id = "INT-005_BETA"
    
    # Encrypt
    cipher = encrypt_employee_id(emp_id)
    assert cipher != emp_id
    
    # Decrypt
    decrypted = decrypt_employee_id(cipher)
    assert decrypted == emp_id
