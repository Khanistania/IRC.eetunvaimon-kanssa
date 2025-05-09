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
    """Send message to all in a channel or to all connected clients"""
    username = authenticated_users.get(sender_conn, "Unknown")
    color = client_colors.get(sender_conn, 15)
    
    if channel:
        # Channel-specific message
        recipients = channels[channel]
    else:
        # Global message (when channel is None)
        recipients = all_clients
    
    for client in recipients:
        if client != sender_conn:  # Don't echo to sender unless you want to
            send_json(client, {
                'action': 'message',
                'from': username,
                'color': color,
                'message': message,
                'channel': channel if channel else None
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
                        
                        # Validate username
                        if len(username) > 12:
                            send_json(conn, {
                                'status': 'error',
                                'message': 'Username must be 12 chars or less.',
                                'retry': True
                            })
                            continue
                        elif not re.match("^[a-zA-Z0-9]+$", username):
                            send_json(conn, {
                                'status': 'error',
                                'message': 'Username can only contain letters and numbers.',
                                'retry': True
                            })
                            continue
                        
                        # Check if username exists
                        if username in users:
                            send_json(conn, {
                                'status': 'error',
                                'message': f'Username "{username}" is already taken.',
                                'retry': True
                            })
                            continue
                        
                        # Register user
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
                                'color': color,
                                'available_channels': list(channels.keys())
                            })
                        except Exception as e:
                            print(f"Error saving user: {e}")
                            send_json(conn, {
                                'status': 'error',
                                'message': 'Server error during registration.',
                                'retry': True
                            })

                    # --- Login ---
                    elif action == 'login':
                        username = data.get('username', '').strip()
                        password = data.get('password', '').strip()
                        
                        with session_lock:
                            # Check if already logged in
                            if username in active_sessions:
                                send_json(conn, {
                                    'action': 'login',
                                    'status': 'error',
                                    'message': 'Account already logged in'
                                })
                                continue
                        
                        # Verify credentials
                        user_data = users.get(username)
                        if not user_data or user_data['password'] != hash_password(password):
                            send_json(conn, {
                                'action': 'login',
                                'status': 'error',
                                'message': 'Invalid credentials'
                            })
                            continue

                        # Create session
                        session_id = os.urandom(16).hex()
                        with session_lock:
                            active_sessions[username] = {
                                'session_id': session_id,
                                'socket': conn,
                                'timestamp': time.time()
                            }
                        
                        authenticated_users[conn] = username
                        client_colors[conn] = user_data.get('color', 15)
                        
                        send_json(conn, {
                            'action': 'login',
                            'status': 'success',
                            'session_id': session_id,
                            'message': 'Login successful',
                            'username': username,
                            'color': user_data.get('color', 15)
                        })

                        
                    # --- Global Messaging ---
                    elif action == 'message':
                        if conn not in authenticated_users:
                            send_json(conn, {
                                'status': 'error', 
                                'message': 'Not authenticated'
                            })
                            continue

                        message = data.get('message', '').strip()
                        channel = data.get('channel', None)
                        
                        if message:
                            if message.startswith('/pm '):
                                # Handle private messages
                                parts = message[4:].split(' ', 1)
                                if len(parts) == 2:
                                    target_user, pm_message = parts
                                    if send_private_message(conn, target_user, pm_message):
                                        # Echo to sender
                                        send_json(conn, {
                                            'action': 'private_message',
                                            'from': 'You',
                                            'to': target_user,
                                            'message': pm_message
                                        })
                                    else:
                                        send_json(conn, {
                                            'status': 'error',
                                            'message': f'User {target_user} not found or offline'
                                        })
                            else:
                                broadcast_message(conn, message, channel)

                    # --- Channel Commands ---
                    elif action == 'command':
                        if conn not in authenticated_users:
                            send_json(conn, {
                                'status': 'error', 
                                'message': 'Not authenticated'
                            })
                            continue

                        cmd = data.get('message', '').strip().lower()
                        username = authenticated_users[conn]
                        
                        if cmd == '/list':
                            # List all channels and their user counts
                            channel_list = []
                            for channel, members in channels.items():
                                channel_list.append(f"{channel} ({len(members)} users)")
                            
                            send_json(conn, {
                                'action': 'system',
                                'message': 'Available channels:\n' + '\n'.join(channel_list) if channel_list else 'No channels available'
                            })
                            
                        elif cmd.startswith('/join '):
                            channel = cmd[6:].strip()
                            if not channel:
                                send_json(conn, {
                                    'action': 'system',
                                    'status': 'error',
                                    'message': 'Please specify a channel name'
                                })
                                continue
                                
                            # Leave all current channels
                            for ch in list(client_channels[conn]):
                                channels[ch].remove(conn)
                                client_channels[conn].remove(ch)
                                broadcast_message(conn, f"{username} has left {ch}", ch)
                            
                            # Join new channel
                            channels[channel].add(conn)
                            client_channels[conn].add(channel)
                            broadcast_message(conn, f"{username} has joined {channel}", channel)
                            send_json(conn, {
                                'action': 'system',
                                'status': 'success',
                                'message': f'Joined channel {channel}',
                                'channel': channel
                            })
                            
                        elif cmd.startswith('/leave'):
                            if not client_channels[conn]:
                                send_json(conn, {
                                    'action': 'system',
                                    'status': 'error',
                                    'message': 'You are not in any channels'
                                })
                                continue
                                
                            # Leave all channels if no specific channel given
                            if cmd == '/leave':
                                for ch in list(client_channels[conn]):
                                    channels[ch].remove(conn)
                                    client_channels[conn].remove(ch)
                                    broadcast_message(conn, f"{username} has left {ch}", ch)
                                send_json(conn, {
                                    'action': 'system',
                                    'status': 'success',
                                    'message': 'Left all channels'
                                })
                            else:
                                # Leave specific channel
                                channel = cmd[7:].strip()
                                if channel in client_channels[conn]:
                                    channels[channel].remove(conn)
                                    client_channels[conn].remove(channel)
                                    broadcast_message(conn, f"{username} has left {channel}", channel)
                                    send_json(conn, {
                                        'action': 'system',
                                        'status': 'success',
                                        'message': f'Left channel {channel}'
                                    })
                                else:
                                    send_json(conn, {
                                        'action': 'system',
                                        'status': 'error',
                                        'message': f'You are not in channel {channel}'
                                    })
                                    
                        elif cmd == '/whoami':
                            send_json(conn, {
                                'action': 'system',
                                'message': f'You are {username}'
                            })
                            
                        elif cmd.startswith('/who '):
                            channel = cmd[5:].strip()
                            if channel in channels:
                                members = [authenticated_users[c] for c in channels[channel] if c in authenticated_users]
                                send_json(conn, {
                                    'action': 'system',
                                    'message': f'Users in {channel}: {", ".join(members)}'
                                })
                            else:
                                send_json(conn, {
                                    'action': 'system',
                                    'status': 'error',
                                    'message': f'Channel {channel} does not exist'
                                })
                                
                        elif cmd == '/help':
                            help_text = """
Available commands:
/join <channel> - Join a channel
/leave [channel] - Leave current or specified channel
/list - List all channels
/who <channel> - List users in a channel
/whoami - Show your username
/pm <user> <message> - Send private message
/help - Show this help
"""
                            send_json(conn, {
                                'action': 'system',
                                'message': help_text.strip()
                            })
                            
                        else:
                            send_json(conn, {
                                'action': 'system',
                                'status': 'error',
                                'message': 'Unknown command. Type /help for available commands.'
                            })

                except json.JSONDecodeError:
                    send_json(conn, {
                        'status': 'error', 
                        'message': 'Invalid JSON'
                    })

    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        # Clean up - leave all channels before disconnecting
        username = authenticated_users.get(conn, None)
        if username:
            # Notify channel members that user is leaving
            for channel in list(client_channels.get(conn, [])):
                channels[channel].remove(conn)
                broadcast_message(conn, f"{username} has disconnected from {channel}", channel)
            
            client_channels.pop(conn, None)
            
            with session_lock:
                if username in active_sessions:
                    del active_sessions[username]
        
        if conn in all_clients:
            all_clients.remove(conn)
        authenticated_users.pop(conn, None)
        client_colors.pop(conn, None)
        conn.close()
        print(f"Connection closed: {addr}")

# Server loop
print(f"Server running on {HOST}:{PORT}")
while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()