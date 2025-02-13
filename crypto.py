import hashlib
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def generate_key_from_string(input_string):
    sha256_hash = hashlib.sha256(input_string.encode()).digest()
    
    return sha256_hash

def encrypt_message(key, plaintext):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    padding_length = 16 - len(plaintext) % 16
    padded_plaintext = plaintext + chr(padding_length) * padding_length  # Preenchendo com o número de bytes necessários
    
    ciphertext = encryptor.update(padded_plaintext.encode()) + encryptor.finalize()
    
    return iv + ciphertext

def decrypt_message(key, ciphertext):
    iv = ciphertext[:16]  
    ciphertext = ciphertext[16:]  

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decrypted = decryptor.update(ciphertext) + decryptor.finalize()
    
    padding_length = decrypted[-1]
    return decrypted[:-padding_length].decode()