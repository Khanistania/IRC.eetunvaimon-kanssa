import socket
import threading
import json
import re
import sys
import time

# ===== NETWORK CONFIGURATION =====
HOST = "10.232.2.253"  # Change to your server IP if needed
PORT = 6668

# Debug mode - set to False in production
DEBUG = False

def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")

def receive_messages(client_socket):
    """Receive messages from the server"""
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
                try:
                    response = json.loads(line)
                    debug_print(f"Received: {response}")
                    
                    if response.get('action') == 'message':
                        print(f"\033[1;38;5;{response['color']}m{response['from']}: {response['message']}\033[0m")
                    elif response.get('status') == 'error':
                        print(f"\nError: {response.get('message')}\n> ", end="", flush=True)
                    elif response.get('action') == 'system':
                        print(f"\nSystem: {response.get('message')}\n> ", end="", flush=True)
                    elif response.get('action') == 'register':
                        if response.get('status') == 'success':
                            print(f"\nRegistration successful! Welcome {response.get('username')}!")
                        else:
                            print(f"\nRegistration error: {response.get('message')}")
                        
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
    """Handle user registration"""
    while True:
        username = get_valid_username()
        password = input("Choose a password: ").strip()
        color_code = choose_color()


        register_data = {
            'action': 'register',
            'username': username,
            'password': password,
            'color': color_code
        }
        
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
    while attempts < 3:
        username = input("\nUsername: ").strip()
        password = input("Password: ").strip()

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
    print("\nType your messages below. Type '/exit' to quit.")
    print("To join a channel: '/join #channelname'")
    print("To leave current channel: '/leave'")
    print("To list channels: '/list'\n")
    
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
                
            # Send message to server
            message_data = {
                'action': 'message' if not msg.startswith('/') else 'command',
                'message': msg
            }
            send_json(client_socket, message_data)
            
        except KeyboardInterrupt:
            print("\nUse '/exit' to quit properly")
        except Exception as e:
            print(f"\nError: {e}")
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
                print(f"\nRegistration successful! Welcome {username}!")
                chat_loop(username, color_code)
                
        elif action == '2':  # Login
            result = login()
            if result:
                username, color_code = result
                print(f"\nLogin successful! Welcome {username}!")
                chat_loop(username, color_code)
                
        elif action == '3':  # Exit
            client_socket.close()
            print("\nGoodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()