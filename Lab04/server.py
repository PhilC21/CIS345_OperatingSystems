import socket
import threading
import sys

# Add function to broadcast messages to all clients
# Write a comment to explain the importance of using a Thread Lock in the client server example.

client_count = 0
client_count_lock = threading.Lock()

clients = [] # list of all connected client sockets
clients_lock = threading.Lock()

# Thread locks make sure that only one thread at a time can change shared data
# (like client_count or the clients list), preventing race conditions between threads.

def broadcast(message, sender_socket=None):
    # broadcast message to all connected clients except the sender
    with clients_lock:
        for client in clients:
            if client is sender_socket:
                continue
            try:
                client.sendall(message.encode('utf-8'))
            except OSError:
                # ignore clients that have already disconnected
                pass

def handle_client(client_socket, address):
    global client_count
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] Handling client {address}")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            message = data.decode('utf-8')

            if message == "/count":
                with client_count_lock:
                    response = f"Active clients: {client_count}"
                client_socket.sendall(response.encode('utf-8'))
            
            elif message.startswith("/broadcast "):
                # `/broadcast <text>` sends a message to all other clients
                text = message[len("/broadcast "):].strip()
                if text:
                    sender_info = f"{address[0]}:{address[1]}"
                    broadcast_msg = f"[Broadcast from {sender_info}] {text}"
                    broadcast(broadcast_msg, sender_socket=client_socket)
                    client_socket.sendall(b"Broadcast sent.")
                else:
                    client_socket.sendall(b"Usage: /broadcast <message>")
            else:
                response = f"Echo: {message}"
                client_socket.sendall(response.encode('utf-8'))

    except ConnectionResetError:
        print(f"[{thread_name}] Client disconnected abruptly")

    finally:
        with client_count_lock:
            client_count -= 1

        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)

        client_socket.close()
        print(f"[{thread_name}] Connection closed for {address}")


def main():
    global client_count
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = '127.0.0.1'
    port = 12345
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}. Type exit to stop.")
    
    def input_thread():
        while True:
            cmd = input()
            if cmd == "exit":
                print("Shutting down server...")
                server_socket.close()
                sys.exit(0)

            elif cmd.startswith("broadcast "):
                # server broadcast to all clients
                text = cmd[len("broadcast "):].strip()
                if text:
                    broadcast(f"[Server Broadcast] {text}")
                    print(f"Broadcast sent to {len(clients)} clients.")
                else:
                    print("Usage: broadcast <message>")

            else:
                print("Unknown command. \nAvailable:")
                print("  exit -> Shut down server.")
                print("  broadcast <message> -> Broadcast messge to all clients.")
                
    threading.Thread(target=input_thread, daemon=True).start()

    while True:
        try:
            client_socket, client_address = server_socket.accept()
        except OSError:
            break
        
        with client_count_lock:
            client_count +=1
        
        with clients_lock:
            clients.append(client_socket)

        #print(f"Accepted connection from {client_address}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,client_address))
        client_handler.start()
        print(f"[Main] clients connected {client_count}")

if __name__ == "__main__":
    main()
