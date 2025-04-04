import socket
import threading
import re

HOST = "127.0.0.1"
PORT = 6667

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

def receive_messages():
    while True:
        try:
            msg = client.recv(1024)
            if not msg:
                break
            print(f"\n{msg.decode()}\n> ", end="")
        except:
            break

thread = threading.Thread(target=receive_messages, daemon=True)
thread.start()


# Lists
colors = [
    ("Light Aqua", 6),
    ("Light Blue", 4),
    ("Yellow", 11),
    ("Bright White", 15),
    ("Light Purple", 13),
    ("Red", 9)
]

def colorchoise():
    while True:
        name = input("Choose your username: ").strip()
        if len(name) > 12:
            print("Username must be 12 letters or less")
            continue
        elif not re.match("^[a-zA-Z0-9]+$", name):
            print("Username cant special characters.")
            continue
        else:
            while True: 
                print("\033[2J\033[H")
                print("Choose a color for your username: ")
                for color, (color_name, color_code) in enumerate(colors, start=1):
                    print(f"{color}. \033[1;38;5;{color_code}m{color_name}\033[0m")

                
                print("\nEnter color number: ", end="")
                try:
                    choice = input()
                    if not choice.strip():
                        raise ValueError
                    
                    choice = int(choice)
                    if 1 <= choice <= len(colors):
                        selected_color = colors[choice-1]
                        return name, selected_color[1]
                    else:
                        print("\033[31mError: Number must be between 1 and", len(colors), "\033[0m")
                        input("Press Enter to try again...")
                        
                except ValueError:
                    print("\033[31mError: Please enter a valid number\033[0m")
                    input("Press Enter to try again...")

name, color_code = colorchoise()
            
while True:
    msg = input(f"\033[1;38;5;{color_code}m{name}\033[0m > ")
    if msg.lower() == 'exit':
        break
    client.sendall(msg.encode())

client.close()