from flask import Flask, render_template, request, jsonify
import os
import threading
import time
import json

# Import với error handling
try:
    from crypto_utils import CryptoManager
    print("✅ CryptoManager imported successfully")
except Exception as e:
    print(f"❌ Error importing CryptoManager: {e}")
    CryptoManager = None

try:
    from socket_server import SecureMessageServer
    print("✅ SecureMessageServer imported successfully")
except Exception as e:
    print(f"❌ Error importing SecureMessageServer: {e}")
    SecureMessageServer = None

app = Flask(__name__)
app.secret_key = 'secure_message_server_secret_key_2024'

# Global variables
server_instance = None
server_thread = None
crypto_manager = CryptoManager() if CryptoManager else None

# Routes
@app.route('/')
def index():
    return render_template('server_index.html')

@app.route('/messages')
def messages():
    return render_template('server_messages.html')

@app.route('/logs')
def logs():
    return render_template('server_logs.html')

# API Routes
@app.route('/api/server-status')
def server_status():
    global server_instance
    try:
        return jsonify({
            'running': server_instance is not None and hasattr(server_instance, 'running') and server_instance.running
        })
    except Exception as e:
        return jsonify({'running': False, 'error': str(e)})

@app.route('/api/start-server', methods=['POST'])
def start_server():
    global server_instance, server_thread

    try:
        if not SecureMessageServer:
            return jsonify({'success': False, 'message': 'SecureMessageServer không khả dụng'})

        if server_instance and server_instance.running:
            return jsonify({'success': False, 'message': 'Server đã đang chạy'})

        server_instance = SecureMessageServer()
        server_thread = threading.Thread(target=server_instance.start_server)
        server_thread.daemon = True
        server_thread.start()

        # Wait a bit to ensure server starts
        time.sleep(1)

        return jsonify({'success': True, 'message': 'Server đã được khởi động'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stop-server', methods=['POST'])
def stop_server():
    global server_instance
    
    try:
        if server_instance:
            server_instance.stop_server()
            server_instance = None
        
        return jsonify({'success': True, 'message': 'Server đã được dừng'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/server-logs')
def get_server_logs():
    if server_instance and hasattr(server_instance, 'logs'):
        return jsonify({'logs': server_instance.logs})
    return jsonify({'logs': []})

@app.route('/api/clear-logs', methods=['POST'])
def clear_logs():
    if server_instance and hasattr(server_instance, 'logs'):
        server_instance.logs.clear()
        return jsonify({'success': True, 'message': 'Đã xóa toàn bộ logs'})
    return jsonify({'success': False, 'message': 'Không thể xóa logs'})

@app.route('/api/connected-clients')
def get_connected_clients():
    try:
        if server_instance and hasattr(server_instance, 'clients'):
            clients_info = []
            for address, client_data in server_instance.clients.items():
                clients_info.append({
                    'address': f"{address[0]}:{address[1]}",
                    'id': client_data.get('id', 'Unknown'),
                    'connected': True
                })
            return jsonify({'clients': clients_info})
        else:
            return jsonify({'clients': []})
    except Exception as e:
        return jsonify({'error': str(e)})

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
        import base64
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

@app.route('/api/last-message')
def last_message():
    global server_instance
    if server_instance and hasattr(server_instance, 'message_history') and server_instance.message_history:
        last_msg = server_instance.message_history[-1]
        return jsonify({'success': True, **last_msg})
    else:
        return jsonify({'success': False, 'message': 'Không có tin nhắn nào'})

@app.route('/api/messages_history', methods=['GET'])
def get_messages_history():
    if server_instance and hasattr(server_instance, 'message_history'):
        return jsonify(server_instance.message_history)
    return jsonify([])

if __name__ == '__main__':
    print("🚀 Starting Secure Message Server...")
    print("🌐 Server will be available at: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True) 