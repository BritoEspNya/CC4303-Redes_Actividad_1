import sys
import socket
from router import create_packet

def parse_header(headers: str) -> dict:
    headers_list = headers.split(";")
    parsed_header = {
        "address": headers_list[0],
        "port": int(headers_list[1]),
        "ttl": int(headers_list[2])
    }
    return parsed_header

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    headers = sys.argv[1]
    IP_router_inicial = sys.argv[2]
    puerto_router_inicial = int(sys.argv[3])

    parsed_header = parse_header(headers)

    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    with open("prueba_router_archivo.txt", "r") as file:
        for line in file:
            parsed_packet = {
                "address": parsed_header["address"],
                "port": parsed_header["port"],
                "ttl": parsed_header["ttl"],
                "msg": line.strip()
            }
            packet = create_packet(parsed_packet)

            socket_udp.sendto(packet, (IP_router_inicial, puerto_router_inicial))

        socket_udp.close()

if __name__ == "__main__":
    main()