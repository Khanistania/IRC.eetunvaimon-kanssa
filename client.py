import socket
import threading
import json
import re
import sys
import msvcrt
import os
from collections import defaultdict

# ===== NETWORK CONFIGURATION =====
HOST = "10.232.2.253"  # Change to your server IP if needed
PORT = 6668

# Debug mode - set to False in production
DEBUG = False

# Global state
current_username = None
current_color_code = 15
current_channel = None  # Track current channel
user_channels = set()   # Track all channels user is in

# Event and lock for server responses
registration_event = threading.Event()
login_event = threading.Event()
login_response = None
login_lock = threading.Lock()
registration_response = None
registration_lock = threading.Lock()

# ===== MESSAGE FORMATTING =====
def format_channel_msg(sender, channel, message, color=15):
    return f"\033[38;5;{color}m{sender}\033[0m [\033[1;34m{channel}\033[0m] {message}"

def format_private_msg(sender, message):
    return f"\033[1;35m[PM from {sender}]\033[0m {message}"

def format_system_msg(message):
    return f"\033[90m[•] {message}\033[0m"

def format_server_msg(message):
    return f"\033[1;33m[Server]\033[0m {message}"

# ===== TERMINAL HELPERS =====
def clear_line():
    """Clear current terminal line"""
    sys.stdout.write('\r\033[K')
    sys.stdout.flush()

def display_prompt():
    """Show input prompt with current channel"""
    if current_channel:
        prompt = f"\033[1;37m[{current_channel}]\033[0m > "
    else:
        prompt = "\033[1;37m>\033[0m "
    sys.stdout.write(prompt)
    sys.stdout.flush()
def show_channel_selection(available_channels):
    print("\nAvailable Channels:")
    for i, channel in enumerate(available_channels, 1):
        print(f"{i}. {channel}")
    
    while True:
        choice = input("\nEnter channel number to join (or 0 to skip): ")
        if choice.isdigit():
            channel_num = int(choice)
            if 0 <= channel_num <= len(available_channels):
                return available_channels[channel_num-1] if channel_num != 0 else None
        print("Invalid input. Please enter a number.")

def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")

def clear_current_line():
    """Clear the current line in terminal"""
    try:
        # Get terminal width safely with fallback
        columns = os.get_terminal_size().columns
    except (AttributeError, OSError):
        columns = 80  # Default fallback width
        
    sys.stdout.write('\r' + ' ' * (columns - 1) + '\r')
    sys.stdout.flush()

def print_system_message(message):
    """Print a system message without interfering with input prompt"""
    clear_current_line()
    print(f"\r\033[1;36mSystem:\033[0m {message}")
    if current_username:
        display_prompt()

def display_prompt():
    """Display the appropriate input prompt based on current state"""
    if current_channel:
        prompt = f"\033[1;38;5;{current_color_code}m{current_username} [{current_channel}]>\033[0m "
    else:
        prompt = f"\033[1;38;5;{current_color_code}m{current_username} >\033[0m "
    sys.stdout.write(prompt)
    sys.stdout.flush()

def receive_messages(client_socket):
    """Receive messages from the server"""
    global registration_response, login_response, current_username, current_color_code, current_channel, user_channels
    
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
                    
                    # Registration response
                    if response.get('action') == 'register':
                        with registration_lock:
                            registration_response = response
                            registration_event.set()
                    
                    # Login response
                    elif response.get('action') == 'login':
                        with login_lock:
                            login_response = response
                            login_event.set()
                    
                    # Error messages
                    elif response.get('status') == 'error':
                        print_system_message(f"Error: {response.get('message')}")
                    
                    # System messages
                    elif response.get('action') == 'system':
                        print_system_message(response.get('message'))
                    
                    # Channel messages
                    elif response.get('action') == 'message':
                        from_user = response.get('from')
                        message = response.get('message')
                        color_code = response.get('color', 15)
                        channel = response.get('channel')
                        
                        # Format the message display
                        if channel:
                            prefix = f"\033[1;38;5;{color_code}m{from_user} [{channel}]>\033[0m"
                        else:
                            prefix = f"\033[1;38;5;{color_code}m{from_user} >\033[0m"
                        
                        clear_current_line()
                        print(f"\r{prefix} {message}")
                        display_prompt()
                    
                    # Private messages
                    elif response.get('action') == 'private_message':
                        from_user = response.get('from')
                        message = response.get('message')
                        color_code = response.get('color', 15)
                        
                        clear_current_line()
                        print(f"\r\033[1;35mPM from {from_user}>\033[0m {message}")
                        display_prompt()
                    
                    # Channel join/leave notifications
                    elif response.get('action') == 'channel_update':
                        channel = response.get('channel')
                        if response.get('type') == 'join':
                            user_channels.add(channel)
                            if not current_channel:
                                current_channel = channel
                        elif response.get('type') == 'leave':
                            user_channels.discard(channel)
                            if current_channel == channel:
                                current_channel = next(iter(user_channels), None)[0] if user_channels else None
                        display_prompt()
                        
                except json.JSONDecodeError:
                    print_system_message("Invalid message from server")
                    
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
    """Handle user login with channel selection"""
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
            # Show channel selection if available
            available_channels = response.get('available_channels', [])
            if available_channels:
                print("\nAvailable Channels:")
                for i, channel in enumerate(available_channels, 1):
                    print(f"{i}. {channel}")
                
                while True:
                    try:
                        choice = input("\nEnter channel number to join (0 to skip): ").strip()
                        if choice == '0':
                            break
                        channel_num = int(choice)
                        if 1 <= channel_num <= len(available_channels):
                            selected_channel = available_channels[channel_num-1]
                            send_json(client_socket, {
                                'action': 'command',
                                'message': f'/join {selected_channel}'
                            })
                            break
                        print(f"Please enter a number between 1 and {len(available_channels)}")
                    except ValueError:
                        print("Invalid input. Please enter a number.")

            return response.get('username'), response.get('color', 15)
        else:
            print(f"\nError: {response.get('message')}")
            attempts += 1
    
    print("Too many failed attempts.")
    return None
# ===== CHAT FUNCTIONALITY =====

def handle_command(command):
    """Handle client-side commands"""
    global current_channel
    
    parts = command.split()
    cmd = parts[0].lower()
    
    if cmd == '/join' and len(parts) > 1:
        channel = parts[1]
        if not channel.startswith('#'):
            channel = '#' + channel
        send_json(client_socket, {
            'action': 'command',
            'message': f'/join {channel}'
        })
        
    elif cmd == '/leave':
        if len(parts) > 1:
            channel = parts[1]
            if not channel.startswith('#'):
                channel = '#' + channel
            send_json(client_socket, {
                'action': 'command',
                'message': f'/leave {channel}'
            })
        else:
            send_json(client_socket, {
                'action': 'command',
                'message': '/leave'
            })
            
    elif cmd == '/list':
        send_json(client_socket, {
            'action': 'command',
            'message': '/list'
        })
        
    elif cmd == '/who' and len(parts) > 1:
        channel = parts[1]
        if not channel.startswith('#'):
            channel = '#' + channel
        send_json(client_socket, {
            'action': 'command',
            'message': f'/who {channel}'
        })
        
    elif cmd == '/pm' and len(parts) > 2:
        target = parts[1]
        message = ' '.join(parts[2:])
        send_json(client_socket, {
            'action': 'message',
            'message': f'/pm {target} {message}'
        })
        
    elif cmd == '/help':
        help_text = """
Available commands:
/join <channel> - Join a channel
/leave [channel] - Leave current or specified channel
/list - List all channels
/who <channel> - List users in a channel
/pm <user> <message> - Send private message
/help - Show this help
/exit - Quit the program
"""
        print_system_message(help_text.strip())
        
    elif cmd == '/exit':
        client_socket.close()
        print("\nGoodbye!")
        sys.exit(0)
        
    else:
        print_system_message("Unknown command. Type /help for available commands.")

def chat_loop(username, color_code=15):
    global current_username, current_color_code
    current_username = username
    current_color_code = color_code
    
    print("\033[1;37m\nWelcome to our IRC Channel.\033[0m")
    print("\nType your messages below. Type '\033[31m/help\033[0m' for command list.")
    display_prompt()
    
    while True:
        try:
            # We use readline to allow for proper line editing
            msg = sys.stdin.readline().strip()
            
            if not msg:
                display_prompt()
                continue
                
            if msg.startswith('/'):
                handle_command(msg)
            else:
                message_data = {
                    'action': 'message',
                    'message': msg,
                    'channel': current_channel
                }
                send_json(client_socket, message_data)
                
            display_prompt()
            
        except KeyboardInterrupt:
            print("\nUse '/exit' to quit properly")
            display_prompt()
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