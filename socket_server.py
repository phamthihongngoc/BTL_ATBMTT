import socket
import threading
import json
import time
from crypto_utils import CryptoManager

class SecureMessageServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.crypto = CryptoManager()
        self.server_socket = None
        self.running = False
        self.logs = []
        self.clients = {}
        self.message_history = []  # Lưu toàn bộ lịch sử tin nhắn
        
    def log(self, message, type='info', details=None):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            'type': type,
            'message': message,
            'timestamp': timestamp,
            'details': details
        }
        self.logs.append(log_entry)
        print(f"[{timestamp}] {type.upper()}: {message}")
        
    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            self.log(f"🚀 Secure Message Server đang chạy tại {self.host}:{self.port}", 'success')

            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, address = self.server_socket.accept()
                    self.log(f"📱 Kết nối từ {address}", 'info')

                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.log(f"❌ Lỗi server: {e}", 'error')
                        break
        except Exception as e:
            self.log(f"❌ Lỗi khởi động server: {e}", 'error')
            self.running = False
                    
    def handle_client(self, client_socket, address):
        try:
            # Handshake
            message = client_socket.recv(1024).decode()
            if message == "Hello!":
                client_socket.send("Ready!".encode())
                self.log(f"✅ Handshake thành công với {address}", 'success')
            else:
                client_socket.send("Invalid handshake".encode())
                return
                
            # Gửi public key
            public_key_pem = self.crypto.get_public_key_pem()
            client_socket.send(public_key_pem.encode())
            
            # Xử lý yêu cầu
            while True:
                try:
                    size_data = client_socket.recv(8).decode()
                    if not size_data:
                        break

                    data_size = int(size_data)
                    data = b''
                    while len(data) < data_size:
                        chunk = client_socket.recv(min(4096, data_size - len(data)))
                        if not chunk:
                            break
                        data += chunk

                    if len(data) != data_size:
                        break
                        
                    request = json.loads(data.decode())
                    
                    if request.get('type') == 'auth':
                        response = self.handle_auth(request, address)
                    elif request.get('type') == 'message':
                        response = self.handle_message(request, address)
                    else:
                        response = {'status': 'error', 'message': 'Loại yêu cầu không được hỗ trợ'}
                        
                    response_bytes = json.dumps(response).encode()
                    size = str(len(response_bytes)).zfill(8).encode()
                    client_socket.send(size)
                    client_socket.send(response_bytes)
                    
                    if request.get('type') == 'message':
                        break
                        
                except json.JSONDecodeError:
                    response = {'status': 'error', 'message': 'JSON không hợp lệ'}
                    response_bytes = json.dumps(response).encode()
                    size = str(len(response_bytes)).zfill(8).encode()
                    client_socket.send(size)
                    client_socket.send(response_bytes)
                    break 
                except Exception as e:
                    response = {'status': 'error', 'message': str(e)}
                    response_bytes = json.dumps(response).encode()
                    size = str(len(response_bytes)).zfill(8).encode()
                    client_socket.send(size)
                    client_socket.send(response_bytes)
                    break 
        except Exception as e:
            self.log(f"❌ Lỗi xử lý client {address}: {e}", 'error')
        finally:
            client_socket.close()
            self.log(f"🔌 Đóng kết nối với {address}", 'info')
            
    def handle_auth(self, request, address):
        try:
            signed_info = request['signed_info']
            encrypted_des_key = request['encrypted_des_key']
            client_id = request['client_id']
            client_public_key_pem = request.get('client_public_key')
            
            # Xác thực chữ ký ID bằng public key của client
            if not self.crypto.verify_signature(client_id, signed_info, client_public_key_pem):
                self.log(f"❌ Xác thực thất bại cho client {client_id}", 'error')
                return {'status': 'NACK', 'error': 'auth', 'message': 'Chữ ký ID không hợp lệ'}
                
            # Giải mã khóa DES
            try:
                self.crypto.decrypt_des_key(encrypted_des_key)
                self.log(f"✅ Giải mã khóa DES thành công cho client {client_id}", 'success')
            except Exception as e:
                self.log(f"❌ Giải mã khóa DES thất bại: {e}", 'error')
                return {'status': 'NACK', 'error': 'key', 'message': 'Không thể giải mã khóa DES'}
                
            # Lưu thông tin client
            self.clients[address] = {
                'id': client_id,
                'des_key': self.crypto.des_key if self.crypto.des_key else None,
                'client_public_key': client_public_key_pem
            }
            
            self.log(f"✅ Xác thực thành công cho client {client_id}", 'success')
            return {'status': 'ACK', 'message': 'Xác thực thành công'}
            
        except Exception as e:
            self.log(f"❌ Lỗi xử lý xác thực: {e}", 'error')
            return {'status': 'NACK', 'error': 'server', 'message': str(e)}
            
    def handle_message(self, request, address):
        try:
            cipher = request['cipher']
            received_hash = request['hash']
            signature = request['sig']
            recipient_id = request.get('recipient_id', 'Server')
            timestamp = request.get('timestamp', 0)
            
            # Kiểm tra tính toàn vẹn bằng SHA-256
            if not self.crypto.verify_integrity(cipher, received_hash):
                self.log(f"❌ Hash không khớp từ client {address}", 'error')
                return {'status': 'NACK', 'error': 'integrity', 'message': 'Hash không khớp'}
                
            # Xác thực chữ ký RSA bằng public key của client
            client_public_key_pem = self.clients[address].get('client_public_key') if address in self.clients else None
            if not self.crypto.verify_signature(cipher, signature, client_public_key_pem):
                self.log(f"❌ Chữ ký không hợp lệ từ client {address}", 'error')
                return {'status': 'NACK', 'error': 'auth', 'message': 'Chữ ký không hợp lệ'}
                
            # Giải mã tin nhắn (cần IV từ message_packet)
            iv = request.get('iv')
            if iv:
                try:
                    decrypted_message = self.crypto.decrypt_text_des(iv, cipher)
                    self.log(f"✅ Tin nhắn hợp lệ từ client {address}: {decrypted_message}", 'success')
                    # Lưu lại message vào lịch sử
                    msg = {
                        'decrypted_text': decrypted_message,
                        'sender_id': self.clients[address]['id'],
                        'timestamp': timestamp
                    }
                    self.message_history.append(msg)
                    return {
                        'status': 'ACK',
                        'message': 'Tin nhắn đã được nhận và xác thực thành công',
                        'timestamp': timestamp
                    }
                except Exception as e:
                    self.log(f"❌ Lỗi giải mã tin nhắn: {e}", 'error')
                    return {'status': 'NACK', 'error': 'decrypt', 'message': 'Không thể giải mã tin nhắn'}
            else:
                self.log(f"❌ Thiếu IV để giải mã tin nhắn", 'error')
                return {'status': 'NACK', 'error': 'decrypt', 'message': 'Thiếu IV để giải mã'}
                
        except Exception as e:
            self.log(f"❌ Lỗi xử lý tin nhắn: {e}", 'error')
            return {'status': 'NACK', 'error': 'server', 'message': str(e)}
            
    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.log("🛑 Server đã được dừng", 'info')

# Alias để tương thích với code cũ
SpotifyCloudServer = SecureMessageServer 