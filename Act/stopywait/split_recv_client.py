import sys

import SocketTCP


def main():
    if len(sys.argv) < 4:
        print("Uso: python3 split_recv_client.py <host> <port> <n>", file=sys.stderr)
        raise SystemExit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    n = int(sys.argv[3])

    payload = b"A" * (2 * n)

    client = SocketTCP.SocketTCP()
    client.connect((host, port))
    client.send(payload)
    client.close()


if __name__ == "__main__":
    main()
