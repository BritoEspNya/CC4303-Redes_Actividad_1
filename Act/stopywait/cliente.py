import sys

import SocketTCP


def run_client(host, port, debug=False):
    data = sys.stdin.buffer.read()
    client_socket = SocketTCP.SocketTCP()
    client_socket.set_debug(debug)
    try:
        client_socket.connect((host, port))
        client_socket.send(data)
        client_socket.close()
    except TimeoutError as exc:
        print(f"Timeout de protocolo: {exc}", file=sys.stderr)
        raise SystemExit(2)


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 cliente.py <host> <port> [--debug]", file=sys.stderr)
        raise SystemExit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    debug = "--debug" in sys.argv[3:]
    run_client(host, port, debug=debug)


if __name__ == "__main__":
    main()