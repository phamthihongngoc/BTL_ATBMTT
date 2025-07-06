import socket
import json
import os
import time
from crypto_utils import CryptoManager

class SecureMessageClient:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.crypto = CryptoManager()
        self.server_public_key = None
        self.socket = None
        self.client_id = "Client_" + str(int(time.time()))
        
    def connect(self):
        """Kết nối đến server và thực hiện handshake"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Handshake - Bước 1: Gửi "Hello!"
            self.socket.send("Hello!".encode())
            response = self.socket.recv(1024).decode()
            
            if response != "Ready!":
                raise Exception(f"Handshake failed: {response}")
                
            # Handshake - Bước 2: Nhận public key từ server
            self.server_public_key = self.socket.recv(2048).decode()
            
            print("✅ Handshake thành công với server")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi kết nối: {e}")
            return False
            
    def send_message(self, message, recipient_id="Server"):
        """Gửi tin nhắn văn bản được mã hóa"""
        try:
            if not self.socket:
                return {'status': 'error', 'message': 'Chưa kết nối đến server'}
                
            # Tạo khóa DES và mã hóa nó bằng RSA công khai của người nhận
            self.crypto.generate_des_key()
            encrypted_des_key = self.crypto.encrypt_des_key(self.server_public_key)
            
            # Ký ID bằng RSA/SHA-256
            signed_info = self.crypto.sign_message(self.client_id)
            
            # Gửi thông tin xác thực và khóa DES
            auth_packet = {
                'type': 'auth',
                'signed_info': signed_info,
                'encrypted_des_key': encrypted_des_key,
                'client_id': self.client_id,
                'client_public_key': self.crypto.get_public_key_pem()
            }
            
            # Gửi auth packet
            auth_data = json.dumps(auth_packet).encode()
            size = str(len(auth_data)).zfill(8)
            self.socket.send(size.encode())
            self.socket.send(auth_data)
            
            # Nhận xác nhận auth
            size_data = self.socket.recv(8)
            if not size_data:
                return {'status': 'error', 'message': 'Không nhận được phản hồi xác thực'}
            response_size = int(size_data.decode())
            
            response_bytes = b''
            while len(response_bytes) < response_size:
                chunk = self.socket.recv(response_size - len(response_bytes))
                if not chunk:
                    break
                response_bytes += chunk
                
            auth_response = json.loads(response_bytes.decode())
            if auth_response.get('status') != 'ACK':
                return {'status': 'error', 'message': 'Xác thực thất bại: ' + auth_response.get('message', '')}
            
            # Mã hóa tin nhắn bằng DES và tạo hash SHA-256
            encrypted_message = self.crypto.encrypt_text_des(message)
            message_packet = {
                'type': 'message',
                'cipher': encrypted_message['cipher'],
                'iv': encrypted_message['iv'],
                'hash': self.crypto.calculate_sha256_hash(encrypted_message['cipher']),
                'sig': self.crypto.sign_message(encrypted_message['cipher']),
                'recipient_id': recipient_id,
                'timestamp': int(time.time())
            }
            
            # Gửi tin nhắn
            message_data = json.dumps(message_packet).encode()
            size = str(len(message_data)).zfill(8)
            self.socket.send(size.encode())
            self.socket.send(message_data)
            
            # Nhận phản hồi
            size_data = self.socket.recv(8)
            if not size_data:
                return {'status': 'error', 'message': 'Không nhận được phản hồi'}
            response_size = int(size_data.decode())
            
            response_bytes = b''
            while len(response_bytes) < response_size:
                chunk = self.socket.recv(response_size - len(response_bytes))
                if not chunk:
                    break
                response_bytes += chunk
                
            response = json.loads(response_bytes.decode())
            
            return response
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def receive_message(self):
        """Nhận tin nhắn từ server"""
        try:
            if not self.socket:
                return {'status': 'error', 'message': 'Chưa kết nối đến server'}
                
            # Nhận kích thước dữ liệu
            size_data = self.socket.recv(8)
            if not size_data:
                return {'status': 'error', 'message': 'Không nhận được dữ liệu'}
            data_size = int(size_data.decode())
            
            # Nhận dữ liệu
            data = b''
            while len(data) < data_size:
                chunk = self.socket.recv(min(4096, data_size - len(data)))
                if not chunk:
                    break
                data += chunk
                
            if len(data) != data_size:
                return {'status': 'error', 'message': 'Dữ liệu không đầy đủ'}
                
            message_data = json.loads(data.decode())
            
            if message_data.get('type') == 'message':
                # Xử lý tin nhắn đến
                return self.handle_incoming_message(message_data)
            else:
                return {'status': 'error', 'message': 'Loại dữ liệu không được hỗ trợ'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def handle_incoming_message(self, message_data):
        """Xử lý tin nhắn đến"""
        try:
            cipher = message_data['cipher']
            received_hash = message_data['hash']
            signature = message_data['sig']
            
            # Kiểm tra tính toàn vẹn bằng SHA-256
            if not self.crypto.verify_integrity(cipher, received_hash):
                return {'status': 'NACK', 'error': 'integrity', 'message': 'Hash không khớp'}
                
            # Xác thực chữ ký RSA
            if not self.crypto.verify_signature(cipher, signature, self.server_public_key):
                return {'status': 'NACK', 'error': 'auth', 'message': 'Chữ ký không hợp lệ'}
                
            # Giải mã tin nhắn (cần IV từ metadata)
            # Trong thực tế, IV sẽ được gửi cùng với tin nhắn
            if 'iv' in message_data:
                decrypted_message = self.crypto.decrypt_text_des(message_data['iv'], cipher)
                return {
                    'status': 'ACK',
                    'message': 'Tin nhắn hợp lệ',
                    'decrypted_text': decrypted_message,
                    'sender_id': message_data.get('sender_id', 'Unknown')
                }
            else:
                return {'status': 'NACK', 'error': 'decrypt', 'message': 'Thiếu IV để giải mã'}
                
        except Exception as e:
            return {'status': 'NACK', 'error': 'decrypt', 'message': str(e)}
            
    def disconnect(self):
        """Đóng kết nối"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("Đã đóng kết nối với server")

# Alias để tương thích với code cũ
SpotifyClient = SecureMessageClient

if __name__ == "__main__":
    client = SpotifyClient()
    
    if client.connect():
        # Test send message
        print("\n=== Test Send Message ===")
        result = client.send_message("Hello, this is a test message!")
        print(f"Send message result: {result}")
        
        # Test receive message
        print("\n=== Test Receive Message ===")
        result = client.receive_message()
        print(f"Receive message result: {result}")
        
        client.disconnect()
