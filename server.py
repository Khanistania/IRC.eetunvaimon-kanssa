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

# Channel structure: {channel_name: set_of_client_connections}
channels = defaultdict(set)
# Track which channels each client is in: {client_conn: set_of_channels}
client_channels = defaultdict(set)
all_clients = set()
session_lock = threading.Lock()
authenticated_users = {}  # {conn: username}
client_colors = {}  # {conn: color_code}
active_sessions = {}  # {username: session_data}
users = {}  # {username: user_data}
DEFAULT_CHANNELS = ["#general", "#random", "#help"]
for channel in DEFAULT_CHANNELS:
    channels[channel] = set() 

DEBUG_MODE = False
USERS_FILE = 'users.json'
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
def broadcast_message(sender_conn, message, channel=None):
    """Send message only to same-channel users"""
    username = authenticated_users.get(sender_conn, "Unknown")
    color = client_colors.get(sender_conn, 15)
    
    recipients = channels[channel] if channel else all_clients
    
    for client in recipients:
        if client != sender_conn:
            send_json(client, {
                'action': 'message',
                'from': username,
                'color': color,
                'message': message,
                'channel': channel
            })

def send_private_message(sender_conn, target_username, message):
    """Send private message to specific user"""
    sender_username = authenticated_users.get(sender_conn, "Unknown")
    sender_color = client_colors.get(sender_conn, 15)
    
    # Find target connection
    target_conn = None
    for conn, username in authenticated_users.items():
        if username == target_username:
            target_conn = conn
            break
    
    if target_conn:
        send_json(target_conn, {
            'action': 'private_message',
            'from': sender_username,
            'color': sender_color,
            'message': message
        })
        return True
    return False

def handle_login(data, conn):
    """Handle user login authentication"""
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    with session_lock:
        # Check if user is already logged in
        if username in active_sessions:
            return {
                'action': 'login',
                'status': 'error',
                'message': 'Account already logged in'
            }
    
    # Verify credentials
    user_data = users.get(username)
    if not user_data or user_data['password'] != hash_password(password):
        return {
            'action': 'login',
            'status': 'error',
            'message': 'Invalid credentials'
        }

    # Create new session
    session_id = os.urandom(16).hex()
    
    with session_lock:
        active_sessions[username] = {
            'session_id': session_id,
            'socket': conn,
            'timestamp': time.time()
        }
    
    return {
        'action': 'login',
        'status': 'success',
        'session_id': session_id,
        'message': 'Login successful', 
        'username': username,
        'color': user_data.get('color', 15),
        'available_channels': list(channels.keys())  # <-- ADD THIS LINE
    }
def handle_client(conn, addr):
    print(f"New connection from {addr}")
    all_clients.add(conn)
    buffer = ""
    username = None  # Track username for connection lifetime
    
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
                
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if DEBUG_MODE:
                    print(f"DEBUG: Raw data from {addr}: {line}")
                try:
                    data = json.loads(line)
                    action = data.get('action')
                    
                    if DEBUG_MODE:
                        print(f"DEBUG: Parsed data from {addr}: {data}")

                    # --- Registration ---
                    if action == 'register':
                        username = data.get('username', '').strip()
                        password = data.get('password', '').strip()
                        color = data.get('color', 15)
                        
                        # [Keep existing validation checks...]
                        
                        # On successful registration:
                        users[username] = {
                            'password': hash_password(password),
                            'color': color
                        }
                        save_users()
                        authenticated_users[conn] = username
                        client_colors[conn] = color
                        
                        # Send success response
                        send_json(conn, {
                            'action': 'register',
                            'status': 'success',
                            'message': f'Registration complete! Welcome {username}!',
                            'username': username,
                            'color': color,
                            'available_channels': list(channels.keys())
                        })
                        
                        # Broadcast to entire server
                        broadcast_message(conn, f" {username} has registered and joined the server!", None)

                    # --- Login ---
                    elif action == 'login':
                        username = data.get('username', '').strip()
                        password = data.get('password', '').strip()
                        
                        # [Keep existing validation checks...]
                        
                        # On successful login:
                        authenticated_users[conn] = username
                        client_colors[conn] = users[username].get('color', 15)
                        
                        # Send success response
                        send_json(conn, {
                            'action': 'login',
                            'status': 'success',
                            'session_id': os.urandom(16).hex(),
                            'message': 'Login successful',
                            'username': username,
                            'color': client_colors[conn],
                            'available_channels': list(channels.keys())
                        })
                        
                        # Broadcast to entire server
                        broadcast_message(conn, f" {username} has joined the server", None)

                    # --- Messaging ---
                    elif action == 'message':
                        if conn not in authenticated_users:
                            send_json(conn, {'status': 'error', 'message': 'Not authenticated'})
                            continue

                        message = data.get('message', '').strip()
                        channel = data.get('channel', None)
                        
                        if message:
                            # Channel messages are automatically isolated to their channel
                            broadcast_message(conn, message, channel)

                    # --- Channel Commands ---
                    elif action == 'command':
                        if conn not in authenticated_users:
                            send_json(conn, {'status': 'error', 'message': 'Not authenticated'})
                            continue

                        cmd = data.get('message', '').strip().lower()
                        username = authenticated_users[conn]
                        
                        if cmd.startswith('/join '):
                            channel = cmd[6:].strip()
                            if not channel.startswith('#'):
                                channel = '#' + channel
                                
                            # Leave current channels first
                            for ch in list(client_channels.get(conn, [])):
                                channels[ch].remove(conn)
                                broadcast_message(conn, f"🚪 {username} has left {ch}", ch)
                            
                            # Join new channel
                            channels[channel].add(conn)
                            client_channels[conn] = {channel}
                            broadcast_message(conn, f" {username} has joined {channel}", channel)
                            send_json(conn, {
                                'action': 'system',
                                'status': 'success',
                                'message': f'Joined {channel}',
                                'channel': channel
                            })

                        elif cmd.startswith('/leave'):
                            # [Similar enhanced leave handling...]
                            broadcast_message(conn, f" {username} has left {channel}", channel)

                except json.JSONDecodeError:
                    send_json(conn, {'status': 'error', 'message': 'Invalid JSON'})

    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        # Handle disconnection
        if username:
            # Notify channels user was in
            for channel in list(client_channels.get(conn, [])):
                channels[channel].remove(conn)
                broadcast_message(conn, f"💤 {username} has left {channel}", channel)
            
            # Notify entire server
            broadcast_message(conn, f" {username} has disconnected from the server", None)
            
            # Clean up
            with session_lock:
                if username in active_sessions:
                    del active_sessions[username]
            client_channels.pop(conn, None)
            authenticated_users.pop(conn, None)
            client_colors.pop(conn, None)
        
        all_clients.discard(conn)
        conn.close()
        print(f"Connection closed: {addr}")

# Server loop
print(f"Server running on {HOST}:{PORT}")
while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()