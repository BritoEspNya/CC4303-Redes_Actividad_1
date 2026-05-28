import sys

import SocketTCP


def main():
    if len(sys.argv) < 4:
        print("Uso: python3 split_recv_server.py <host> <port> <n>", file=sys.stderr)
        raise SystemExit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    n = int(sys.argv[3])

    server = SocketTCP.SocketTCP()
    server.bind((host, port))
    conn, _ = server.accept()

    part1 = conn.recv(n)
    part2 = conn.recv(n)

    expected = b"A" * (2 * n)

    print("PART1_LEN", len(part1))
    print("PART2_LEN", len(part2))
    print("REASSEMBLY_OK", (part1 + part2) == expected)

    conn.recv_close()


if __name__ == "__main__":
    main()
