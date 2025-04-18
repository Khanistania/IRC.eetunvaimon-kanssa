import socket
import threading
import json
import re
import sys
import msvcrt

# ===== NETWORK CONFIGURATION =====
HOST = "10.232.2.253"  # Change to your server IP if needed
PORT = 6668

# Debug mode - set to False in production
DEBUG = False

current_username = None
current_color_code = 15

def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")

registration_event = threading.Event()
login_event = threading.Event()
login_response = None
login_lock = threading.Lock()
registration_response = None
registration_lock = threading.Lock()

def receive_messages(client_socket):
    """Receive messages from the server"""
    global registration_response, login_response, current_username, current_color_code
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
                if DEBUG:
                    print(f"DEBUG: Raw data received: {line}")
                try:
                    response = json.loads(line)
                    if DEBUG:
                        print(f"DEBUG: Parsed response: {response}")
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
                    elif response.get('status') == 'error':
                        print(f"\rError: {response.get('message')}")
                        if current_username:
                            sys.stdout.write(f"\033[1;38;5;{current_color_code}m{current_username} >\033[0m ")
                            sys.stdout.flush()
                    elif response.get('action') == 'system':
                        print(f"\rSystem: {response.get('message')}")
                        if current_username:
                            sys.stdout.write(f"\033[1;38;5;{current_color_code}m{current_username} \033[0m ")
                            sys.stdout.flush()
                    elif response.get('action') == 'message':
                        from_user = response.get('from')
                        message = response.get('message')
                        color_code = response.get('color', 15)  # Oletusväri, jos ei määritelty
                        colored_username = f"\033[1;38;5;{color_code}m{from_user} >\033[0m"
                        # Tulosta viesti välilyönnillä >-merkin sijaan
                        print(f"\r{colored_username} {message}")
                        # Tulosta käyttäjän oma prompt uudelleen
                        if current_username:
                            sys.stdout.write(f"\033[1;38;5;{current_color_code}m{current_username} >\033[0m ")
                            sys.stdout.flush()
                        
                except json.JSONDecodeError:
                    print("\rInvalid message from server")
                    if current_username:
                        sys.stdout.write(f"\033[1;38;5;{current_color_code}m{current_username}\033[0m > ")
                        sys.stdout.flush()
                    
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

def get_hidden_password(prompt):
    """Get password with asterisks displayed for each character (Windows only)"""
    print(prompt, end="", flush=True)
    password = []
    while True:
        char = msvcrt.getch()  # Read a single keypress
        char = char.decode('utf-8')
        if char == '\r' or char == '\n':  # Enter key
            print()  # Move to next line
            break
        elif char == '\b':  # Backspace
            if password:
                password.pop()  # Remove last character
                sys.stdout.write('\b \b')  # Move cursor back, overwrite with space, move back again
                sys.stdout.flush()
        else:
            password.append(char)
            sys.stdout.write('*')  # Print asterisk
            sys.stdout.flush()
    return ''.join(password)

def send_json(sock, data):
    """Safely send JSON data to a specific socket"""
    try:
        payload = json.dumps(data) + '\n'
        if DEBUG:
            print(f"DEBUG: Sending to server: {payload}")
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
    global registration_response
    while True:
        username = get_valid_username()
        password = get_hidden_password("Choose a password: ")
        color_code = choose_color()

        register_data = {
            'action': 'register',
            'username': username,
            'password': password,
            'color': color_code
        }
        
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
    
    while attempts < 3:
        username = input("\nUsername: ").strip()
        password = get_hidden_password("Password: ")

        if not send_json(client_socket, {
            'action': 'login',
            'username': username,
            'password': password
        }):
            attempts += 1
            continue
        if DEBUG:
            print("DEBUG: Waiting for login response...")
        login_event.wait(5)
        
        with login_lock:
            if DEBUG:
                print(f"DEBUG: Login response received: {login_response}")
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

def chat_loop(username, color_code=15):
    global current_username, current_color_code
    current_username = username
    current_color_code = color_code
    print("\nType your messages below. Type '/exit' to quit.")
    print("To join a channel: '/join #channelname'")
    print("To leave current channel: '/leave'")
    print("To list channels: '/list'\n")
    
    while True:
        try:
            prompt = f"\033[1;38;5;{color_code}m{username} >\033[0m "
            sys.stdout.write(prompt)
            sys.stdout.flush()
            msg = sys.stdin.readline().strip()
            
            if not msg:
                continue
                
            if msg.lower() == '/exit':
                client_socket.close()
                print("\nGoodbye!")
                sys.exit(0)
                
            message_data = {
                'action': 'message' if not msg.startswith('/') else 'command',
                'message': msg
            }
            send_json(client_socket, message_data)
            
        except KeyboardInterrupt:
            print("\nUse '/exit' to quit properly")
        except Exception as e:
            print(f"\nConnection error: {e}")
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
                chat_loop(username, color_code)
                
        elif action == '2':  # Login
            result = login()
            if result:
                username, color_code = result
                chat_loop(username, color_code)
                
        elif action == '3':  # Exit
            client_socket.close()
            print("\nGoodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()