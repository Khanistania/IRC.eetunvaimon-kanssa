import socket
import threading
import json
import re
import sys
<<<<<<< HEAD
=======
import time
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479

# ===== NETWORK CONFIGURATION =====
HOST = "10.232.2.253"  # Change to your server IP if needed
PORT = 6668

# Debug mode - set to False in production
DEBUG = False

def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")

<<<<<<< HEAD
registration_event = threading.Event()
login_event = threading.Event()
login_response = None
login_lock = threading.Lock()
registration_response = None
registration_lock = threading.Lock()

def receive_messages(client_socket):
    """Receive messages from the server"""
    global registration_response, login_response
=======
def receive_messages(client_socket):
    """Receive messages from the server"""
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
    buffer = ""
    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                print("\nServer disconnected. Press Enter to exit...")
                sys.exit()
                
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
<<<<<<< HEAD
                print(f"DEBUG: Raw data received: {line}")  # Lisää tämä: näyttää raakadatan
                try:
                    response = json.loads(line)
                    print(f"DEBUG: Parsed response: {response}")  # Lisää tämä: näyttää käsitellyn JSONin
                    debug_print(f"Received: {response}")
                    
                    # Rekisteröinti
                    if response.get('action') == 'register':
                        with registration_lock:
                            registration_response = response
                            registration_event.set()
                    
                    # Kirjautuminen
                    elif response.get('action') == 'login':
                        with login_lock:
                            login_response = response
                            login_event.set()
                    
                    # Muut viestit
=======
                try:
                    response = json.loads(line)
                    debug_print(f"Received: {response}")
                    
                    if response.get('action') == 'message':
                        print(f"\033[1;38;5;{response['color']}m{response['from']}: {response['message']}\033[0m")
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
                    elif response.get('status') == 'error':
                        print(f"\nError: {response.get('message')}\n> ", end="", flush=True)
                    elif response.get('action') == 'system':
                        print(f"\nSystem: {response.get('message')}\n> ", end="", flush=True)
<<<<<<< HEAD
                    elif response.get('action') == 'message':
                        print(f"\n{response.get('from')}: {response.get('message')}\n> ", end="", flush=True)
=======
                    elif response.get('action') == 'register':
                        if response.get('status') == 'success':
                            print(f"\nRegistration successful! Welcome {response.get('username')}!")
                        else:
                            print(f"\nRegistration error: {response.get('message')}")
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
                        
                except json.JSONDecodeError:
                    print("\nInvalid message from server\n> ", end="", flush=True)
                    
        except Exception as e:
            print(f"\nConnection error: {e}")
            sys.exit()

# Create socket and connect
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client_socket.connect((HOST, PORT))
except ConnectionRefusedError:
    print("Error: Could not connect to server.")
    exit(1)

# Start receive thread
thread = threading.Thread(target=receive_messages, args=(client_socket,))
thread.daemon = True
thread.start()

# ===== COLOR DEFINITIONS =====
colors = [
    ("Light Aqua", 6),
    ("Light Blue", 4),
    ("Yellow", 11),
    ("Bright White", 15),
    ("Light Purple", 13),
    ("Red", 9)
]

# ===== USER AUTHENTICATION =====

def choose_action():
    """Ask the user to choose to register or login"""
    while True:
        print("\n1. Register\n2. Login\n3. Exit")
        choice = input("Choose an option: ").strip()
        if choice in ['1', '2', '3']:
            return choice
        print("Invalid choice. Please choose 1, 2, or 3.")

def get_valid_username():
    """Get a valid username from user"""
    while True:
        username = input("Choose your username (a-z, 0-9, max 12 chars): ").strip()
        if len(username) > 12:
            print("Username must be 12 letters or less")
            continue
        elif not re.match("^[a-zA-Z0-9]+$", username):
            print("Username can't have special characters.")
            continue
        return username

def choose_color():
    """Let user choose a color"""
    print("\nChoose a color for your username: ")
    for i, (color_name, code) in enumerate(colors):
        print(f"{i+1}. \033[1;38;5;{code}m{color_name}\033[0m")
    
    while True:
        try:
            choice = input("\nEnter color number: ")
            color_choice = int(choice)
            if 1 <= color_choice <= len(colors):
                return colors[color_choice-1][1]
            print(f"Please enter a number between 1 and {len(colors)}")
        except ValueError:
            print("Please enter a valid number")

def send_json(sock, data):
    """Safely send JSON data to a specific socket"""
    try:
        payload = json.dumps(data) + '\n'
<<<<<<< HEAD
        print(f"DEBUG: Sending to server: {payload}")  # Lisää tämä: näyttää lähetetyn datan
=======
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
        sock.sendall(payload.encode())
        debug_print(f"Sent to {sock.getpeername()}: {data}")
        return True
    except (ConnectionResetError, BrokenPipeError):
        debug_print(f"Connection lost with {sock.getpeername()}")
        return False
    except Exception as e:
        debug_print(f"Send error: {e}")
        return False

def register():
<<<<<<< HEAD
    global registration_response
=======
    """Handle user registration"""
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
    while True:
        username = get_valid_username()
        password = input("Choose a password: ").strip()
        color_code = choose_color()

<<<<<<< HEAD
=======

>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
        register_data = {
            'action': 'register',
            'username': username,
            'password': password,
            'color': color_code
        }
        
<<<<<<< HEAD
        if not send_json(client_socket, register_data):
            return None

        # ODOTA 5 SEKUNTIA
        registration_event.wait(5)
        
        with registration_lock:
            response = registration_response
            registration_event.clear()
            registration_response = None

        if not response:
            print("Registration timed out.")
            return None
            
        if response.get('status') == 'success':
            return response.get('username'), response.get('color', 15)
        else:
            print(f"\nError: {response.get('message')}")
            if not response.get('retry', False):
                return None

def login():
    """Handle user login"""
    global login_response
    attempts = 0
    
=======
        send_json(client_socket, register_data)
        
        try:            
            response = json.loads(client_socket.recv(1024).decode())
            
            if response.get('status') == 'success':
                print(f"\nRegistering succesful, welcome {username}.")
                return username, color_code
            else:
                print(f"\nError: {response.get('message')}")
                if not response.get('retry', False):
                    return None
        except Exception as e:
            print(f"\nError during registration: {e}")
            return None

def login():
    """Handle user login"""
    attempts = 0
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
    while attempts < 3:
        username = input("\nUsername: ").strip()
        password = input("Password: ").strip()

<<<<<<< HEAD
        if not send_json(client_socket, {
            'action': 'login',
            'username': username,
            'password': password
        }):
            attempts += 1
            continue

        print("DEBUG: Waiting for login response...")  # Lisää tämä: näyttää odotuksen alkamisen
        login_event.wait(5)  # Pidennetty 5 sekuntiin, kuten aiemmin ehdotin
        
        with login_lock:
            print(f"DEBUG: Login response received: {login_response}")  # Lisää tämä: näyttää vastauksen
            response = login_response
            login_event.clear()
            login_response = None

        if not response:
            print("Login timed out.")
            attempts += 1
            continue
            
        if response.get('status') == 'success':
            return response.get('username'), response.get('color', 15)
        else:
            print(f"\nError: {response.get('message')}")
            attempts += 1
    
    print("Too many failed attempts.")
    return None
# ===== CHAT FUNCTIONALITY =====

# KORJAA ASIAKKAAN CHAT_LOOP
def chat_loop(username, color_code=15):
=======
        send_json(client_socket,{
            'action': 'login',
            'username': username,
            'password': password
        })
        
        try:
            response = json.loads(client_socket.recv(1024).decode())
            
            if response.get('status') == 'success':
                color = response.get('color', 15)  # Use server-provided color
                print(f"\nLogin successful! Welcome {username}!")
                return username, color
            else:
                print(f"\nError: {response.get('message')}")
                attempts += 1
                
        except Exception as e:
            print(f"\nConnection error: {e}")
            attempts += 1
    
    print("Too many failed attempts. Please try again later.")
    return None
# ===== CHAT FUNCTIONALITY =====

def chat_loop(username, color_code=15):
    """Main chat loop after successful login/registration"""
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
    print("\nType your messages below. Type '/exit' to quit.")
    print("To join a channel: '/join #channelname'")
    print("To leave current channel: '/leave'")
    print("To list channels: '/list'\n")
    
<<<<<<< HEAD
    while True:
        try:
=======
    # Clear any pending data
    client_socket.settimeout(0.1)
    try:
        while client_socket.recv(1024):
            pass
    except:
        pass
    client_socket.settimeout(None)
    
    while True:
        try:
            # Better input handling
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
            prompt = f"\033[1;38;5;{color_code}m{username}\033[0m > "
            sys.stdout.write(prompt)
            sys.stdout.flush()
            msg = sys.stdin.readline().strip()
            
            if not msg:
                continue
                
            if msg.lower() == '/exit':
                client_socket.close()
                print("\nGoodbye!")
                sys.exit(0)
                
<<<<<<< HEAD
=======
            # Send message to server
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
            message_data = {
                'action': 'message' if not msg.startswith('/') else 'command',
                'message': msg
            }
            send_json(client_socket, message_data)
            
        except KeyboardInterrupt:
            print("\nUse '/exit' to quit properly")
        except Exception as e:
<<<<<<< HEAD
            print(f"\nConnection error: {e}")
=======
            print(f"\nError: {e}")
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
            client_socket.close()
            sys.exit(1)

# ===== MAIN PROGRAM =====
def main():
    print(f"Connecting to {HOST}:{PORT}...")
    
    while True:
        action = choose_action()
        
        if action == '1':  # Register
            result = register()
            if result:
                username, color_code = result
<<<<<<< HEAD
=======
                print(f"\nRegistration successful! Welcome {username}!")
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
                chat_loop(username, color_code)
                
        elif action == '2':  # Login
            result = login()
            if result:
                username, color_code = result
<<<<<<< HEAD
=======
                print(f"\nLogin successful! Welcome {username}!")
>>>>>>> 094f9ff17da006ad473cbc5ec1d1e9d3a0b6d479
                chat_loop(username, color_code)
                
        elif action == '3':  # Exit
            client_socket.close()
            print("\nGoodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()