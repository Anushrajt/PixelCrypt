"""
Cryptographic Engine - AES-256-GCM Authenticated Encryption
============================================================
Implements military-grade AES-256-GCM with PBKDF2-HMAC-SHA256 key derivation.
Features:
- 256-bit symmetric encryption key
- 100,000 PBKDF2 iterations with unique 16-byte cryptographically secure salt
- 96-bit (12-byte) initialization vector (IV / Nonce)
- Galois/Counter Mode (GCM) provides built-in 128-bit authentication tag
  guaranteeing BOTH Confidentiality and Tamper-Proof Integrity
"""

import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


PBKDF2_ITERATIONS = 100_000
SALT_SIZE = 16
NONCE_SIZE = 12


def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a 256-bit (32 bytes) key from a user passphrase using PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_message(plaintext: str, password: str) -> bytes:
    """
    Encrypts a plaintext string using AES-256-GCM.
    Returns serialized binary payload:
    [16 bytes Salt] + [12 bytes Nonce] + [Ciphertext + 16 bytes Auth Tag]
    """
    if not plaintext:
        raise ValueError("Plaintext message cannot be empty.")
    if not password:
        raise ValueError("Encryption password cannot be empty.")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt)

    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)

    # Payload format: Salt (16B) + Nonce (12B) + Encrypted Data with Tag
    return salt + nonce + ciphertext_with_tag


def decrypt_message(encrypted_payload: bytes, password: str) -> str:
    """
    Decrypts an AES-256-GCM payload.
    Raises ValueError on incorrect password or tampered ciphertext (auth tag mismatch).
    """
    if len(encrypted_payload) < (SALT_SIZE + NONCE_SIZE + 16):
        raise ValueError("Corrupt or invalid encrypted payload: Data too short.")

    salt = encrypted_payload[:SALT_SIZE]
    nonce = encrypted_payload[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext_with_tag = encrypted_payload[SALT_SIZE + NONCE_SIZE:]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data=None)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError("Decryption failed: Incorrect password or data has been tampered with!") from e


if __name__ == "__main__":
    msg = "Top Secret PIN: 9842 & Offshore Account: #CH-77492"
    pwd = "CyberMasterKey@2026"
    print("[*] Original Message:", msg)
    
    enc = encrypt_message(msg, pwd)
    print(f"[+] Encrypted Payload Length: {len(enc)} bytes (Salt: 16B, Nonce: 12B, Tag: 16B)")
    
    dec = decrypt_message(enc, pwd)
    print("[+] Decrypted Result:", dec)
    assert msg == dec, "Verification test failed!"
    print("[*] AES-256-GCM Test PASSED perfectly!")
