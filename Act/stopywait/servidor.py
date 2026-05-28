import sys

import SocketTCP


def run_server(host, port, debug=False):
    server_socket = SocketTCP.SocketTCP()
    server_socket.set_debug(debug)
    server_socket.bind((host, port))

    connection, _ = server_socket.accept()
    connection.set_debug(debug)

    # Para este flujo de prueba basta un recv grande y luego cerrar.
    data = connection.recv(10**7)
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    connection.recv_close()


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 servidor.py <host> <port> [--debug]", file=sys.stderr)
        raise SystemExit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    debug = "--debug" in sys.argv[3:]
    run_server(host, port, debug=debug)


if __name__ == "__main__":
    main()