import json
import os
import socket
import threading
from collections import defaultdict
import hashlib
import re
import time

HOST = '10.232.2.253'  # Listen on all interfaces
PORT = 6668

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

channels = defaultdict(set)
all_clients = set()
session_lock = threading.Lock()
authenticated_users = {}
client_colors = {}
active_sessions = {}
users = {}

DEBUG_MODE = False

USERS_FILE = 'users.json'

def load_users():
    """Safely load users from JSON file"""
    if not os.path.exists(USERS_FILE):
        return {}
    
    try:
        with open(USERS_FILE, 'r') as f:
            # Check if file is empty
            if os.path.getsize(USERS_FILE) == 0:
                return {}
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f" Error loading users: {e} - Starting with empty database")
        return {}
    
users = load_users()
if not isinstance(users, dict):  # Ensure it's always a dictionary
    print(" Invalid user data format - Resetting to empty database")
    users = {}
    
def save_users():
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Couldnt save user data {e}")

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def send_json(conn, data):
    try:
        conn.sendall((json.dumps(data) + '\n').encode())
    except:
        pass

def broadcast_message(sender_conn, message):
    """Broadcast message to all connected clients"""
    username = authenticated_users.get(sender_conn, "Unknown")
    color = client_colors.get(sender_conn, 15)
    
    for client in all_clients:
        if client != sender_conn:  # Don't echo to sender
            send_json(client, {
                'action': 'message',
                'from': username,
                'color': color,
                'message': message
            })

def handle_login (data, conn):
    username = data.get('username', '').strip()
            
    with session_lock:
        if username in active_sessions:
            return {
                'action': 'login',
                'status': 'error',
                'message': 'Account already logged in'
            }
    user_data = users.get(username)
    if not user_data or user_data['password']!= hash_password(data.get('password', '')):
        return {
            'action': 'login',
            'status': 'error',
            'message': 'Invalid credentials'
        }

    session_id = os.urandom(16).hex()
        
    return {
        'action': 'login',
        'status': 'success',
        'session_id': session_id,
        'message': 'Login successful', 
        'username': username,
        'color': user_data.get('color', 15)
    }
        

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    all_clients.add(conn)
    buffer = ""
    
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
                
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if DEBUG_MODE:
                    print(f"DEBUG: Raw data from {addr}: {line}")  # Lisää tämä: näyttää raakadatan
                try:
                    data = json.loads(line)
                    action = data.get('action')
                    
                    if DEBUG_MODE:
                        print(f"DEBUG: Parsed data from {addr}: {data}")  # Lisää tämä: näyttää käsitellyn JSONin

                    # --- Registration ---
                    if action == 'register':
                        username = data.get('username', '').strip()
                        password = data.get('password', '').strip()
                        color = data.get('color', 15)
                        if DEBUG_MODE:
                            print(f"DEBUG: Register attempt - Username: {username}, Color: {color}")
                        
                        # Validate username
                        if len(username) > 12:
                            send_json(conn, {
                                'status': 'error',
                                'message': 'Username must be 12 chars or less.',
                                'retry': True  # <-- Tämä on jo oikein, sallii uuden yrityksen
                            })
                            continue
                        elif not re.match("^[a-zA-Z0-9]+$", username):
                            send_json(conn, {
                                'status': 'error',
                                'message': 'Username can only contain letters and numbers.',
                                'retry': True  # <-- Tämä on jo oikein
                            })
                            continue
                        
                        # Tarkista onko käyttäjätunnus varattu
                        if username in users:
                            send_json(conn, {
                                'status': 'error',
                                'message': f'Username "{username}" is already taken. Please choose another one.',
                                'retry': True  # <-- TÄRKEÄ: Tämä sallii uuden yrityksen
                            })
                            continue
                        
                        # Rekisteröi käyttäjä
                        try:
                            users[username] = {
                                'password': hash_password(password),
                                'color': color
                            }
                            save_users()
                            authenticated_users[conn] = username
                            client_colors[conn] = color
                            send_json(conn, {
                                'action': 'register',
                                'status': 'success',
                                'message': f'Registration complete! Welcome {username}!',
                                'username': username,
                                'color': color
                            })
                    
                        except Exception as e:
                            print(f"Error saving user: {e}")
                            send_json(conn, {
                                'status': 'error',
                                'message': 'Server error during registration. Please try again.',
                                'retry': True
                            })

                    # --- Login ---
                    elif action == 'login':
                        # Get credentials first
                        username = data.get('username', '').strip()
                        password = data.get('password', '').strip()
                        
                        if DEBUG_MODE:
                            print(f"DEBUG: Login attempt - Username: {username}")

                        # Call login handler
                        response = handle_login(data, conn)  # Changed to handle_login
                        
                        # Process response
                        if response.get('status') == 'success':
                            session_id = response['session_id']
                            with session_lock:
                                active_sessions[username] = {
                                    'session_id': session_id,
                                    'socket': conn,
                                    'timestamp': time.time()
                                }
                            authenticated_users[conn] = username
                            client_colors[conn] = response.get('color', 15)
                        
                        # Send final response
                        if DEBUG_MODE:
                            status = "successful" if response['status'] == 'success' else "failed"
                            print(f"DEBUG: Login {status} - Sending: {response}")
                        send_json(conn, response)
                        
                    # --- Messaging ---
                    elif action == 'message':
                        if conn not in authenticated_users:
                            send_json(conn, {
                                'status': 'error', 
                                'message': 'Not authenticated'
                            })
                            continue

                        message = data.get('message', '').strip()
                        if message:
                            broadcast_message(conn, message)

                    # --- Commands ---
                    elif action == 'command':
                        if conn not in authenticated_users:
                            send_json(conn, {
                                'status': 'error', 
                                'message': 'Not authenticated'
                            })
                            continue

                        cmd = data.get('message', '').strip().lower()
                        if cmd == '/list':
                            send_json(conn, {
                                'action': 'system',
                                'message': f'Available channels: {list(channels.keys())}'
                            })
                        elif cmd.startswith('/join '):
                            channel = cmd[6:].strip()
                            channels[channel].add(conn)
                            send_json(conn, {
                                'action': 'system',
                                'message': f'Joined channel {channel}'
                            })
                        elif cmd == '/leave':
                            for ch in list(channels.keys()):
                                if conn in channels[ch]:
                                    channels[ch].remove(conn)
                                    send_json(conn, {
                                        'action': 'system',
                                        'message': f'Left channel {ch}'
                                    })

                except json.JSONDecodeError:
                    send_json(conn, {
                        'status': 'error', 
                        'message': 'Invalid JSON'
                    })

    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        # Clean up
        if conn in all_clients:
            all_clients.remove(conn)
            
        username = authenticated_users.pop(conn, None)
        client_colors.pop(conn, None)
        
        if username:
            with session_lock:
                if username in active_sessions:
                    del active_sessions[username]
        
        conn.close()
        print(f"Connection closed: {addr}")


# Server loop
print(f"Server running on {HOST}:{PORT}")
while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()