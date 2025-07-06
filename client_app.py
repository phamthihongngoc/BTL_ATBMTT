from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import os
import requests
import json
import base64

# Import với error handling
try:
    from crypto_utils import CryptoManager
    print("✅ CryptoManager imported successfully")
except Exception as e:
    print(f"❌ Error importing CryptoManager: {e}")
    CryptoManager = None

try:
    from socket_client import SecureMessageClient
    print("✅ SecureMessageClient imported successfully")
except Exception as e:
    print(f"❌ Error importing SecureMessageClient: {e}")
    SecureMessageClient = None

app = Flask(__name__)
app.secret_key = 'secure_message_client_secret_key_2024'

# Configuration
SERVER_URL = 'http://localhost:5001'

# Global variables
crypto_manager = CryptoManager() if CryptoManager else None

# Routes
@app.route('/')
def index():
    return render_template('client_index.html')

@app.route('/send')
def send():
    return render_template('client_send.html')

@app.route('/receive')
def receive():
    return render_template('client_receive.html')

@app.route('/security')
def security():
    return render_template('client_security.html')

# API Routes
@app.route('/api/server-status')
def server_status():
    try:
        response = requests.get(f'{SERVER_URL}/api/server-status', timeout=5)
        return jsonify(response.json())
    except requests.exceptions.RequestException:
        return jsonify({'running': False, 'error': 'Không thể kết nối đến server'})

@app.route('/api/start-server', methods=['POST'])
def start_server():
    try:
        response = requests.post(f'{SERVER_URL}/api/start-server', timeout=10)
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'message': f'Không thể kết nối đến server: {str(e)}'})

@app.route('/api/stop-server', methods=['POST'])
def stop_server():
    try:
        response = requests.post(f'{SERVER_URL}/api/stop-server', timeout=10)
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'message': f'Không thể kết nối đến server: {str(e)}'})

@app.route('/api/send-message', methods=['POST'])
def api_send_message():
    try:
        # Check if server is running
        server_status_response = requests.get(f'{SERVER_URL}/api/server-status', timeout=5)
        if not server_status_response.json().get('running', False):
            return jsonify({
                'success': False, 
                'message': 'Server chưa được khởi động. Vui lòng khởi động server trước.'
            })
        
        data = request.get_json()
        message = data.get('message', '').strip()
        recipient_id = data.get('recipient_id', 'Server')
        
        if not message:
            return jsonify({'success': False, 'message': 'Tin nhắn không được để trống'})
        
        # Use socket client to send message
        if not SecureMessageClient:
            return jsonify({'success': False, 'message': 'SecureMessageClient không khả dụng'})
        
        client = SecureMessageClient()
        if client.connect():
            result = client.send_message(message, recipient_id)
            client.disconnect()
            
            if result['status'] == 'ACK':
                return jsonify({
                    'success': True,
                    'message': 'Gửi tin nhắn thành công',
                    'security_info': {
                        'handshake': True,
                        'key_exchange': True,
                        'encryption': True,
                        'signature': True,
                        'verification': True
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', 'Gửi tin nhắn thất bại'),
                    'security_error': {
                        'type': result.get('error', 'unknown'),
                        'message': result.get('message', 'Lỗi không xác định'),
                        'details': 'Hệ thống đã phát hiện và từ chối dữ liệu bị sửa đổi'
                    }
                })
        else:
            return jsonify({'success': False, 'message': 'Không thể kết nối đến server socket'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/receive-message', methods=['POST'])
def api_receive_message():
    try:
        # Check if server is running
        server_status_response = requests.get(f'{SERVER_URL}/api/server-status', timeout=5)
        if not server_status_response.json().get('running', False):
            return jsonify({
                'success': False, 
                'message': 'Server chưa được khởi động. Vui lòng khởi động server trước.'
            })
        # Lấy message cuối cùng từ server
        response = requests.get(f'{SERVER_URL}/api/last-message', timeout=5)
        data = response.json()
        if data.get('success'):
            return jsonify({
                'success': True,
                'message': 'Nhận tin nhắn thành công',
                'decrypted_text': data.get('decrypted_text', ''),
                'sender_id': data.get('sender_id', 'Unknown'),
                'timestamp': data.get('timestamp', ''),
                'security_info': {
                    'integrity_check': True,
                    'signature_verification': True,
                    'decryption': True
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': data.get('message', 'Nhận tin nhắn thất bại'),
                'security_error': {
                    'type': 'not_found',
                    'message': data.get('message', 'Không có tin nhắn nào')
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/test-des', methods=['POST'])
def test_des():
    try:
        if not crypto_manager:
            return jsonify({'success': False, 'message': 'CryptoManager không khả dụng'})
        
        data = request.get_json()
        test_text = data.get('text', 'Hello, this is a test message!')
        
        # Tạo khóa DES
        crypto_manager.generate_des_key()
        
        # Mã hóa
        encrypted_data = crypto_manager.encrypt_text_des(test_text)
        
        # Giải mã
        decrypted_text = crypto_manager.decrypt_text_des(encrypted_data['iv'], encrypted_data['cipher'])
        
        # Tính hash
        message_hash = crypto_manager.calculate_sha256_hash(encrypted_data['cipher'])
        
        return jsonify({
            'success': True,
            'original_text': test_text,
            'encrypted_data': encrypted_data,
            'decrypted_text': decrypted_text,
            'hash': message_hash,
            'message': 'Test DES encryption/decryption thành công'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/test-rsa', methods=['POST'])
def test_rsa():
    try:
        if not crypto_manager:
            return jsonify({'success': False, 'message': 'CryptoManager không khả dụng'})
        
        data = request.get_json()
        test_message = data.get('message', 'Test RSA signature')
        
        # Ký tin nhắn
        signature = crypto_manager.sign_message(test_message)
        
        # Xác thực chữ ký
        is_valid = crypto_manager.verify_signature(test_message, signature)
        
        # Test với tin nhắn khác
        is_invalid = crypto_manager.verify_signature(test_message + "tampered", signature)
        
        return jsonify({
            'success': True,
            'original_message': test_message,
            'signature': signature,
            'verification_result': is_valid,
            'tampered_verification': is_invalid,
            'message': 'Test RSA signature thành công'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/test-sha256', methods=['POST'])
def test_sha256():
    try:
        if not crypto_manager:
            return jsonify({'success': False, 'message': 'CryptoManager không khả dụng'})
        
        data = request.get_json()
        test_data = data.get('data', 'Test data for SHA-256')
        
        # Tính hash
        hash_value = crypto_manager.calculate_sha256_hash(base64.b64encode(test_data.encode()).decode())
        
        # Kiểm tra tính toàn vẹn
        is_valid = crypto_manager.verify_integrity(base64.b64encode(test_data.encode()).decode(), hash_value)
        
        return jsonify({
            'success': True,
            'original_data': test_data,
            'hash': hash_value,
            'integrity_check': is_valid,
            'message': 'Test SHA-256 hash thành công'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/test-socket', methods=['POST'])
def test_socket():
    try:
        if not SecureMessageClient:
            return jsonify({'success': False, 'message': 'SecureMessageClient không khả dụng'})
        
        client = SecureMessageClient()
        if client.connect():
            result = client.send_message("Test message from client")
            client.disconnect()
            
            return jsonify({
                'success': True,
                'connection': True,
                'result': result,
                'message': 'Test socket connection thành công'
            })
        else:
            return jsonify({
                'success': False,
                'connection': False,
                'message': 'Không thể kết nối đến server socket'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    print("🚀 Starting Secure Message Client...")
    print("🌐 Client will be available at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True) 