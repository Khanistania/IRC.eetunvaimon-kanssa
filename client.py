import socket
import threading

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

while True:
    msg = input("> ")
    if msg.lower() == 'exit':
        break
    client.sendall(msg.encode())

client.close()