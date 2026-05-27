import SocketTCP

def run_server(host, port):
    server_socket = SocketTCP.SocketTCP()
    server_socket.bind((host, port))

    print("Esperando datos en localhost:8000...")
    connection, _ = server_socket.accept()
    # Recibir usando Stop & Wait; imprimimos datos a medida que llegan
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            continue
        try:
            print(chunk.decode("utf-8"), end="")
        except UnicodeDecodeError:
            print(chunk)


def main():
    run_server("localhost", 8000)


if __name__ == "__main__":
    main()