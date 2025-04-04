import socket
import threading

HOST = '127.0.0.1'
PORT = 6667

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    clients.append(conn)
    while True:
        try:
            msg = conn.recv(1024)
            if not msg:
                break
            print(f"{addr} says: {msg.decode()}")
            for client in clients:
                if client != conn:
                    client.sendall(msg)
        except:
            break

    clients.remove(conn)
    conn.close()
    print(f"Connection closed: {addr}")

print(f"Server listening on {HOST}:{PORT}...")

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()