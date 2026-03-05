"""
Encryption Module - AES-256 encryption for uploaded documents.
Encrypts files at rest before any processing begins.
"""
import os
from pathlib import Path
from cryptography.fernet import Fernet
from ..config import ENCRYPTION_KEY


def _get_cipher():
    """Get or create Fernet cipher with the configured key."""
    key = ENCRYPTION_KEY
    if not key:
        key_file = Path(__file__).resolve().parent.parent.parent / ".encryption_key"
        if key_file.exists():
            key = key_file.read_text().strip()
        else:
            key = Fernet.generate_key().decode()
            key_file.write_text(key)
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_file(source_path: str, dest_path: str) -> str:
    """
    Encrypt a file using AES-256 (Fernet).
    Returns the path to the encrypted file.
    """
    cipher = _get_cipher()
    with open(source_path, "rb") as f:
        data = f.read()
    encrypted = cipher.encrypt(data)
    with open(dest_path, "wb") as f:
        f.write(encrypted)
    return dest_path


def decrypt_file(encrypted_path: str) -> bytes:
    """
    Decrypt a file and return raw bytes.
    """
    cipher = _get_cipher()
    with open(encrypted_path, "rb") as f:
        encrypted_data = f.read()
    return cipher.decrypt(encrypted_data)


def encrypt_text(text: str) -> str:
    """Encrypt a text string."""
    cipher = _get_cipher()
    return cipher.encrypt(text.encode()).decode()


def decrypt_text(encrypted_text: str) -> str:
    """Decrypt a text string."""
    cipher = _get_cipher()
    return cipher.decrypt(encrypted_text.encode()).decode()
