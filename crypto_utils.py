import os
import hashlib
import base64
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

class CryptoManager:
    def __init__(self):
        self.des_key = None
        self.private_key = None
        self.public_key = None
        self.generate_rsa_keys()
        
    def generate_rsa_keys(self):
        """Tạo cặp khóa RSA 2048-bit"""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
    def generate_des_key(self):
        """Tạo khóa DES 64-bit hoặc TripleDES nếu DES không có"""
        from cryptography.hazmat.primitives.ciphers import algorithms
        if hasattr(algorithms, 'DES'):
            self.des_key = os.urandom(8)  # 64-bit key cho DES
            self._use_triple_des = False
        else:
            self.des_key = os.urandom(24)  # 192-bit key cho TripleDES
            self._use_triple_des = True
        return self.des_key
        
    def encrypt_des_key(self, public_key_pem=None):
        """Mã hóa khóa DES bằng RSA với OAEP + SHA-256"""
        if public_key_pem:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode()
            )
        else:
            public_key = self.public_key
            
        encrypted_key = public_key.encrypt(
            self.des_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted_key).decode()
        
    def decrypt_des_key(self, encrypted_key_b64):
        """Giải mã khóa DES bằng RSA với OAEP + SHA-256"""
        encrypted_key = base64.b64decode(encrypted_key_b64)
        self.des_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return self.des_key
        
    def encrypt_text_des(self, text):
        """Mã hóa văn bản bằng DES (CFB mode) hoặc TripleDES nếu không có DES"""
        from cryptography.hazmat.primitives.ciphers import algorithms
        if not self.des_key:
            self.generate_des_key()
        iv = os.urandom(8)
        if hasattr(algorithms, 'DES') and not getattr(self, '_use_triple_des', False):
            alg = algorithms.DES(self.des_key)
        else:
            alg = algorithms.TripleDES(self.des_key)
        cipher = Cipher(
            alg,
            modes.CFB(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        text_bytes = text.encode('utf-8')
        ciphertext = encryptor.update(text_bytes) + encryptor.finalize()
        return {
            'iv': base64.b64encode(iv).decode(),
            'cipher': base64.b64encode(ciphertext).decode()
        }
        
    def decrypt_text_des(self, iv_b64, cipher_b64):
        """Giải mã văn bản bằng DES (CFB mode) hoặc TripleDES nếu không có DES"""
        from cryptography.hazmat.primitives.ciphers import algorithms
        if not self.des_key:
            raise ValueError("DES key not available")
        iv = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(cipher_b64)
        if hasattr(algorithms, 'DES') and not getattr(self, '_use_triple_des', False):
            alg = algorithms.DES(self.des_key)
        else:
            alg = algorithms.TripleDES(self.des_key)
        cipher = Cipher(
            alg,
            modes.CFB(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext.decode('utf-8')
        
    def calculate_sha256_hash(self, ciphertext_b64):
        """Tính SHA-256 hash của ciphertext"""
        ciphertext = base64.b64decode(ciphertext_b64)
        return hashlib.sha256(ciphertext).hexdigest()
        
    def sign_message(self, message):
        """Ký tin nhắn bằng RSA/SHA-256"""
        message_bytes = message.encode('utf-8')
        signature = self.private_key.sign(
            message_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()
        
    def verify_signature(self, message, signature_b64, public_key_pem=None):
        """Xác thực chữ ký RSA/SHA-256"""
        if public_key_pem:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode()
            )
        else:
            public_key = self.public_key
            
        message_bytes = message.encode('utf-8')
        signature = base64.b64decode(signature_b64)
        
        try:
            public_key.verify(
                signature,
                message_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except:
            return False
            
    def get_public_key_pem(self):
        """Lấy public key dưới dạng PEM"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
    def verify_integrity(self, ciphertext_b64, received_hash):
        """Kiểm tra tính toàn vẹn bằng SHA-256"""
        calculated_hash = self.calculate_sha256_hash(ciphertext_b64)
        return calculated_hash == received_hash

    def encrypt_message(self, text):
        """Mã hóa tin nhắn hoàn chỉnh với DES và tạo hash"""
        encrypted_data = self.encrypt_text_des(text)
        message_hash = self.calculate_sha256_hash(encrypted_data['cipher'])
        signature = self.sign_message(encrypted_data['cipher'])
        
        return {
            'cipher': encrypted_data['cipher'],
            'hash': message_hash,
            'sig': signature
        }

    def decrypt_message(self, encrypted_data):
        """Giải mã tin nhắn và kiểm tra tính toàn vẹn"""
        cipher = encrypted_data['cipher']
        received_hash = encrypted_data['hash']
        signature = encrypted_data['sig']
        
        # Kiểm tra hash
        if not self.verify_integrity(cipher, received_hash):
            raise ValueError("Hash verification failed")
            
        # Xác thực chữ ký
        if not self.verify_signature(cipher, signature):
            raise ValueError("Signature verification failed")
            
        # Giải mã (cần IV từ handshake hoặc metadata)
        # Trong thực tế, IV sẽ được gửi cùng với ciphertext
        # Ở đây chúng ta giả định IV đã được lưu trữ
        if hasattr(self, 'current_iv'):
            return self.decrypt_text_des(self.current_iv, cipher)
        else:
            raise ValueError("IV not available for decryption")
