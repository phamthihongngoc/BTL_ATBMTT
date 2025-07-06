#!/usr/bin/env python3
"""
Script để chạy cả Server và Client cùng lúc
"""

import subprocess
import sys
import time
import os

def run_server():
    """Chạy server trong process riêng"""
    print("🚀 Khởi động Secure Message Server...")
    server_process = subprocess.Popen([sys.executable, 'server_app.py'])
    return server_process

def run_client():
    """Chạy client trong process riêng"""
    print("📱 Khởi động Secure Message Client...")
    client_process = subprocess.Popen([sys.executable, 'client_app.py'])
    return client_process

def main():
    print("=" * 60)
    print("🔐 Ứng dụng Bảo mật Tin nhắn Văn bản")
    print("   DES + RSA + SHA-256")
    print("=" * 60)
    
    try:
        # Khởi động server trước
        server_process = run_server()
        time.sleep(2)  # Đợi server khởi động
        
        # Khởi động client
        client_process = run_client()
        
        print("\n✅ Cả hai ứng dụng đã được khởi động!")
        print("📊 Server: http://localhost:5001")
        print("📱 Client: http://localhost:5000")
        print("\n💡 Hướng dẫn sử dụng:")
        print("   1. Truy cập http://localhost:5001 để khởi động server socket")
        print("   2. Truy cập http://localhost:5000 để gửi/nhận tin nhắn")
        print("   3. Nhấn Ctrl+C để dừng cả hai ứng dụng")
        
        # Đợi cho đến khi người dùng nhấn Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Đang dừng các ứng dụng...")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return 1
    
    finally:
        # Dừng các process
        try:
            if 'server_process' in locals():
                server_process.terminate()
                server_process.wait()
                print("✅ Server đã được dừng")
            
            if 'client_process' in locals():
                client_process.terminate()
                client_process.wait()
                print("✅ Client đã được dừng")
                
        except Exception as e:
            print(f"⚠️ Lỗi khi dừng process: {e}")
    
    print("👋 Tạm biệt!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 