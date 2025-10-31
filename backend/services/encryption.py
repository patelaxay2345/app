from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64

class EncryptionService:
    def __init__(self):
        # Get encryption key from environment (must be 32 bytes for AES-256)
        key_str = os.environ.get('ENCRYPTION_KEY', 'this-is-a-32-byte-encryption-key-for-aes256-change-me')
        self.key = key_str.encode()[:32].ljust(32, b'\x00')
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-256-CBC"""
        if not plaintext:
            return ""
        
        try:
            # Generate random IV
            iv = os.urandom(16)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Pad plaintext to multiple of 16 bytes
            plaintext_bytes = plaintext.encode()
            padding_length = 16 - (len(plaintext_bytes) % 16)
            padded_plaintext = plaintext_bytes + bytes([padding_length] * padding_length)
            
            # Encrypt
            ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
            
            # Return IV + ciphertext as base64
            return base64.b64encode(iv + ciphertext).decode()
        except Exception as e:
            raise Exception(f"Encryption error: {str(e)}")
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt ciphertext using AES-256-CBC"""
        if not encrypted:
            return ""
        
        try:
            # Decode base64
            data = base64.b64decode(encrypted)
            
            # Extract IV and ciphertext
            iv = data[:16]
            ciphertext = data[16:]
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove padding
            padding_length = padded_plaintext[-1]
            plaintext = padded_plaintext[:-padding_length]
            
            return plaintext.decode()
        except Exception as e:
            raise Exception(f"Decryption error: {str(e)}")
