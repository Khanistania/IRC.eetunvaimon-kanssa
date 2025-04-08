import socket
import threading
from collections import defaultdict

HOST = '10.232.2.253'
PORT = 6668

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

channels = defaultdict(set)
all_clients = set()

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    all_clients.add(conn)
    try:
        while True:
            msg = conn.recv(1024).decode().strip()  
            if not msg:
                break
            
            print(f"{addr} says: {msg}")
            
            if msg.startswith('/join '):
                parts = msg.split(' ')
                if len(parts) < 2:
                    conn.sendall("Error: Missing channel name".encode())
                    continue
                    
                channel = parts[1]
                if not channel.startswith('#'):
                    conn.sendall("Error: Channels start with #".encode())
                    continue
                
                # Leave existing channels
                for ch in list(channels.keys()):
                    if conn in channels[ch]:
                        channels[ch].remove(conn)
                        broadcast(ch, f"A user left {ch}")
                
                # Join new channel
                channels[channel].add(conn)
                broadcast(channel, f"New user has joined {channel}", exclude=conn)
                conn.sendall(f"Joined {channel}".encode())
                
            elif msg == '/list':
                channel_list = ', '.join(channels.keys()) or "No active channels"
                conn.sendall(f"Active channels: {channel_list}".encode())
                
            elif msg == '/leave':
                left = False
                for channel in list(channels.keys()):
                    if conn in channels[channel]:
                        channels[channel].remove(conn)
                        broadcast(channel, f"A user left {channel}")
                        conn.sendall(f"Left {channel}".encode())
                        left = True
                        break
                if not left:
                    conn.sendall("You're not in any channel".encode())
                    
            else:
                user_channels = [ch for ch in channels if conn in channels[ch]]
                if user_channels:
                    for channel in user_channels:
                        broadcast(channel, msg, exclude=conn)
                else:
                    conn.sendall("Join a channel first with /join #channel".encode())
                    
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        for channel in list(channels.keys()):
            if conn in channels[channel]:
                channels[channel].remove(conn)
                broadcast(channel, "A user disconnected")
        all_clients.remove(conn)
        conn.close()
        print(f"Connection closed: {addr}")

def broadcast(channel, message, exclude=None):
    for conn in channels[channel]:
        if conn != exclude:
            try:
                conn.sendall(f"[{channel}] {message}\n".encode())
            except:
                if conn in channels[channel]:
                    channels[channel].remove(conn)

print(f"IRC Server running on {HOST}:{PORT}")
print("Supported commands:")
print("/join #channel - Join a channel")
print("/leave - Leave current channel")
print("/list - List all channels")

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()