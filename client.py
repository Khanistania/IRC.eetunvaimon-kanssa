import socket
import threading
import re

# ===== NETWORK CONFIGURATION =====
HOST = "127.0.0.1"
PORT = 6667

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

# ===== MESSAGE RECEIVING THREAD =====
def receive_messages():
    while True:
        try:
            msg = client.recv(1024)
            if not msg:
                break
            print(f"\033[48;5;{bg_color}m\033[1;38;5;{color_code}m{msg.decode()}\033[0m\n> ", end="")
        except:
            break

thread = threading.Thread(target=receive_messages, daemon=True)
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

background_colors = [
    ("Default (Black)", 0),
    ("Dark Gray", 8),
    ("Dark Blue", 17),
    ("Dark Green", 22),
    ("Dark Red", 52),
    ("Dark Purple", 54)
]

# ===== USER PREFERENCES SETUP =====
def user_preferences():
    # Username validation loop
    while True:
        name = input("Choose your username: ").strip()
        if len(name) > 12:
            print("Username must be 12 letters or less")
            continue
        elif not re.match("^[a-zA-Z0-9]+$", name):
            print("Username cant special characters.")
            continue
        
        # Color selection section
        username_color = None
        while True: 
            print("\033[2J\033[H")  # Clear screen
            print("Choose a color for your username: ")
            for color, (color_name, color_code) in enumerate(colors, start=1):
                print(f"{color}. \033[1;38;5;{color_code}m{color_name}\033[0m")

            # Color selection input handling
            print("\nEnter color number: ", end="") 
            try:
                choice = input()
                if not choice.strip():
                    raise ValueError
                
                choice = int(choice)
                if 1 <= choice <= len(colors):
                    selected_color = colors[choice-1]
                    username_color = selected_color[1]
                    break
                else:
                    print("\033[31mError: Number must be between 1 and", len(colors), "\033[0m")
                    input("Press Enter to try again...")
                    
            except ValueError:
                print("\033[31mError: Please enter a valid number\033[0m")
                input("Press Enter to try again...")

        # Background color selection (same pattern as username color)
        bg_color = None
        while True:
            print("\033[2J\033[H")
            print("Choose a color for your chat background: ")
            for bg_num, (bg_name, bg_code) in enumerate(background_colors, start=1):
                print(f"{bg_num}. \033[48;5;{bg_code}m{bg_name:^20}\033[0m")

            print("\nEnter background color number: ", end="")
            try:
                bg_choice = input()
                if not bg_choice.strip():
                    raise ValueError
                
                bg_choice = int(bg_choice)
                if 1 <= bg_choice <= len(background_colors):
                    selected_bg = background_colors[bg_choice-1]
                    bg_color = selected_bg[1]
                    break
                else:
                    print("\033[31mError: Number must be between 1 and", len(background_colors), "\033[0m")
                    input("Press Enter to try again...")
                    
            except ValueError:
                print("\033[31mError: Please enter a valid number\033[0m")
                input("Press Enter to try again...")

        return name, username_color, bg_color

# ===== MAIN CHAT LOOP =====
name, color_code, bg_color = user_preferences()

while True:
    msg = input(f"\033[1;38;5;{color_code}m{name}\033[0m > ")
    if msg.lower() == 'exit':
        break
    client.sendall(msg.encode())

client.close()
