import SocketTCP

MAX_PAYLOAD = 16


def read_file_bytes():
    path = input("Ruta del archivo: ").strip()
    with open(path, "rb") as file:
        return file.read()


def iter_chunks(data, chunk_size=MAX_PAYLOAD):
    for offset in range(0, len(data), chunk_size):
        yield data[offset : offset + chunk_size]


def run_client(host, port):
    data = read_file_bytes()
    client_socket = SocketTCP.SocketTCP()
    client_socket.connect((host, port))
    sent = client_socket.send(data)
    # opcional: imprimir bytes enviados
    print(f"Enviados {sent} bytes")


def main():
    run_client("localhost", 8000)


if __name__ == "__main__":
    main()