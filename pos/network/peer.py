import socket
import threading


class Handler:

    def handle(self, data: str):
        pass


class Peer:
    MSG_LEN = 2048

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []

    def connect(self, peer_host, peer_port) -> None:
        try:
            connection = self.socket.connect((peer_host, peer_port))
            self.connections.append(connection)
            print(f"Connected to {peer_host}:{peer_port}")
        except socket.error as e:
            print(f"Failed to connect to {peer_host}:{peer_port}. Error: {e}")

    def listen(self, handler: Handler) -> None:
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        print(f"Listening for connections on {self.host}:{self.port}")

        while True:
            conn, addr = self.socket.accept()
            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(data.decode())
                    handler.handle(data.decode())

    def send_data(self, data) -> None:
        for connection in self.connections:
            try:
                connection.sendall(data.encode())
            except socket.error as e:
                print(f"Failed to send data. Error: {e}")

    def start(self, handler: Handler) -> None:
        listen_thread = threading.Thread(target=self.listen, args=[handler])
        listen_thread.start()

    def __del__(self):
        self.socket.close()
