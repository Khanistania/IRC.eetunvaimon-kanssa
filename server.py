import json
import os
import socket
import threading
from collections import defaultdict
import hashlib
import time

HOST = '10.232.2.226'
PORT = 6668

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

channels = defaultdict(set)
client_channels = defaultdict(set)
all_clients = set()
session_lock = threading.Lock()
authenticated_users = {}
client_colors = {}
active_sessions = {}
users = {}
DEFAULT_CHANNELS = ["#general", "#random", "#help"]
for channel in DEFAULT_CHANNELS:
    channels[channel] = set()

DEBUG_MODE = False
USERS_FILE = 'users.json'

# Lataa käyttäjätiedot tiedostosta
# Lataa käyttäjät JSON-tiedostosta, jos se existsi
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r') as f:
            if os.path.getsize(USERS_FILE) == 0:
                return {}
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        # Virhe käyttäjien lataamisessa: {e} - Aloitetaan tyhjällä tietokannalla
        print(f"Virhe käyttäjien lataamisessa: {e} - Aloitetaan tyhjällä tietokannalla")
        return {}

users = load_users()
if not isinstance(users, dict):
    # Virheellinen käyttäjädatan muoto - Nollataan tyhjäksi tietokannaksi
    print("Virheellinen käyttäjädatan muoto - Nollataan tyhjäksi tietokannaksi")
    users = {}

# Tallentaa käyttäjätiedot tiedostoon
# Tallentaa käyttäjädatan JSON-muodossa tiedostoon
def save_users():
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        # Käyttäjädatan tallentaminen epäonnistui: {e}
        print(f"Käyttäjädatan tallentaminen epäonnistui: {e}")

# Luo salasanan hajautusarvon
# Muuntaa salasanan SHA-256-hajautusarvoksi
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# Lähettää JSON-datan asiakkaalle
# Koodaa ja lähettää JSON-muotoisen datan asiakkaan yhteyden kautta
def send_json(conn, data):
    try:
        conn.sendall((json.dumps(data) + '\n').encode())
    except:
        pass

# Lähettää viestin kaikille kanavan tai palvelimen asiakkaille
# Lähettää viestin määritetylle kanavalle tai kaikille asiakkaille, poislukien lähettäjä
def broadcast_message(sender_conn, message, channel=None):
    username = authenticated_users.get(sender_conn, "Tuntematon")
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

# Lähettää yksityisviestin tietylle käyttäjälle
# Lähettää viestin vain kohdekäyttäjälle, jos käyttäjä löytyy
def send_private_message(sender_conn, target_username, message):
    sender_username = authenticated_users.get(sender_conn, "Tuntematon")
    sender_color = client_colors.get(sender_conn, 15)
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

# Käsittelee käyttäjän kirjautumisen
# Tarkistaa käyttäjätunnuksen ja salasanan, luo istunnon onnistuneen kirjautumisen jälkeen
def handle_login(data, conn):
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    with session_lock:
        if username in active_sessions:
            return {
                'action': 'login',
                'status': 'error',
                'message': 'Tili on jo kirjautuneena'
            }
    user_data = users.get(username)
    if not user_data or user_data['password'] != hash_password(password):
        return {
            'action': 'login',
            'status': 'error',
            'message': 'Virheelliset tunnukset'
        }
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
        'message': 'Kirjautuminen onnistui',
        'username': username,
        'color': user_data.get('color', 15),
        'available_channels': list(channels.keys())
    }

# Käsittelee asiakasyhteyden tapahtumat
# Hallitsee asiakkaan viestien vastaanoton, käsittelyn ja yhteyden sulkemisen
def handle_client(conn, addr):
    # Uusi yhteys osoitteesta {addr}
    print(f"Uusi yhteys osoitteesta {addr}")
    all_clients.add(conn)
    buffer = ""
    username = None
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if DEBUG_MODE:
                    # DEBUG: Raaka data osoitteesta {addr}: {line}
                    print(f"DEBUG: Raaka data osoitteesta {addr}: {line}")
                try:
                    data = json.loads(line)
                    action = data.get('action')
                    if DEBUG_MODE:
                        # DEBUG: Jäsennelty data osoitteesta {addr}: {data}
                        print(f"DEBUG: Jäsennelty data osoitteesta {addr}: {data}")

                    if action == 'register':
                        username = data.get('username', '').strip()
                        password = data.get('password', '').strip()
                        color = data.get('color', 15)
                        if username in users:
                            send_json(conn, {
                                'action': 'register',
                                'status': 'error',
                                'message': 'Käyttäjätunnus on jo varattu'
                            })
                            continue
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
                            'message': f'Rekisteröityminen valmis! Tervetuloa {username}!',
                            'username': username,
                            'color': color,
                            'available_channels': list(channels.keys())
                        })
                        broadcast_message(conn, f" {username} on rekisteröitynyt ja liittynyt palvelimelle!", None)

                    elif action == 'login':
                        response = handle_login(data, conn)
                        if response['status'] == 'success':
                            username = response['username']
                            authenticated_users[conn] = username
                            client_colors[conn] = response['color']
                            send_json(conn, response)
                            broadcast_message(conn, f" {username} on liittynyt palvelimelle", None)
                        else:
                            send_json(conn, response)

                    elif action == 'message':
                        if conn not in authenticated_users:
                            send_json(conn, {'status': 'error', 'message': 'Ei autentikoitu'})
                            continue
                        message = data.get('message', '').strip()
                        channel = data.get('channel', None)
                        if not channel or channel not in channels or conn not in channels[channel]:
                            send_json(conn, {
                                'action': 'system',
                                'message': 'Sinun täytyy liittyä kanavalle lähettääksesi viestejä'
                            })
                            continue
                        if message:
                            broadcast_message(conn, message, channel)

                    elif action == 'command':
                        if conn not in authenticated_users:
                            send_json(conn, {'status': 'error', 'message': 'Ei autentikoitu'})
                            continue
                        cmd = data.get('message', '').strip().lower()
                        username = authenticated_users[conn]
                        if cmd.startswith('/join '):
                            channel = cmd[6:].strip()
                            if not channel.startswith('#'):
                                channel = '#' + channel
                            if client_channels[conn]:
                                current_channel = next(iter(client_channels[conn]))
                                channels[current_channel].remove(conn)
                                client_channels[conn].clear()
                                broadcast_message(conn, f"🚪 {username} on poistunut kanavalta {current_channel}", current_channel)
                            channels[channel].add(conn)
                            client_channels[conn] = {channel}
                            broadcast_message(conn, f" {username} on liittynyt kanavalle {channel}", channel)
                            send_json(conn, {
                                'action': 'channel_update',
                                'type': 'join',
                                'channel': channel
                            })
                        elif cmd == '/leave':
                            if client_channels[conn]:
                                channel = next(iter(client_channels[conn]))
                                channels[channel].remove(conn)
                                client_channels[conn].clear()
                                broadcast_message(conn, f" {username} on poistunut kanavalta {channel}", channel)
                                send_json(conn, {
                                    'action': 'channel_update',
                                    'type': 'leave',
                                    'channel': channel
                                })
                            else:
                                send_json(conn, {
                                    'action': 'system',
                                    'message': 'Et ole millään kanavalla'
                                })

                except json.JSONDecodeError:
                    send_json(conn, {'status': 'error', 'message': 'Virheellinen JSON'})
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        if username:
            if client_channels[conn]:
                channel = next(iter(client_channels[conn]))
                channels[channel].remove(conn)
                broadcast_message(conn, f"💤 {username} on poistunut kanavalta {channel}", channel)
            broadcast_message(conn, f" {username} on katkaissut yhteyden palvelimelle", None)
            with session_lock:
                if username in active_sessions:
                    del active_sessions[username]
            client_channels.pop(conn, None)
            authenticated_users.pop(conn, None)
            client_colors.pop(conn, None)
        all_clients.discard(conn)
        conn.close()
        # Yhteys suljettu: {addr}
        print(f"Yhteys suljettu: {addr}")

# Palvelin käynnissä osoitteessa {HOST}:{PORT}
print(f"Palvelin käynnissä osoitteessa {HOST}:{PORT}")
while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()