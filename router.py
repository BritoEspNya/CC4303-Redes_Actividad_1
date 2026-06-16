import sys
import socket

from route_handler import RouteHandler

def router(router_IP: str, router_port: int, router_routes_filename: str) -> None:
    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind((router_IP, router_port))

    router_handler = RouteHandler(router_routes_filename)

    while True:
        data, addr = socket_udp.recvfrom(1024)
        parsed_data = parse_packet(data)
        
        if parsed_data["ttl"] > 0:
            if parsed_data["address"] == router_IP and parsed_data["port"] == router_port:
                print(f"Mensaje recibido: {parsed_data["msg"]}")
            else:
                next_hop = check_routes(router_handler, (parsed_data["address"], parsed_data["port"]))
                if next_hop[0] is not None and next_hop[1] is not None:
                    parsed_data["ttl"] -= 1
                    new_data = create_packet(parsed_data)

                    print(f"...redirigiendo paquete {new_data} con destino final {parsed_data['port']} desde {router_port} hacia {next_hop}")
                    socket_udp.sendto(new_data, next_hop)
                else:
                    print(f"No hay rutas hacia {parsed_data['port']} para paquete {data}")
        else:
            print(f"Se recibió paquete {data} con TTL 0")

def check_routes(handler: RouteHandler, destination_address: tuple[str, int]) -> tuple[str, int]:
    return handler.check_routes(destination_address)


def parse_packet(IP_packet: bytes) -> dict:
    # Decode address
    address = ".".join(str(octet) for octet in IP_packet[:4])

    # Decode port
    port = int.from_bytes(IP_packet[4:6])

    # Decode TTL
    ttl = IP_packet[6]

    # Decode message
    msg = IP_packet[7:].decode("utf-8")

    parsed_packet = {
        "address": address,
        "port": port,
        "ttl": ttl,
        "msg": msg
    }

    return parsed_packet


def create_packet(parsed_IP_packet: dict) -> bytes:
    if len(parsed_IP_packet) < 3:
        raise ValueError("Invalid package format. Expected dict{addresss, port, msg}")

    # Encode address
    address_octets = parsed_IP_packet["address"].split(".", 4)
    address_bytes = b''.join(int(octet).to_bytes(1) for octet in address_octets)

    # Encode port
    port_bytes = parsed_IP_packet["port"].to_bytes(2)

    # Encode ttl
    ttl_bytes = parsed_IP_packet["ttl"].to_bytes(1)

    # Encode message
    msg_bytes = parsed_IP_packet["msg"].encode('utf-8')

    packet = b''.join([address_bytes, port_bytes, ttl_bytes, msg_bytes])

    return packet


def main():
    if len(sys.argv) < 4: # Expected: router.py router_IP router_port router_routes_filename
        sys.exit(1)
    
    router_IP = sys.argv[1]
    router_port = int(sys.argv[2])
    router_routes_filename = sys.argv[3]

    router(router_IP, router_port, router_routes_filename)

if __name__ == "__main__":
    main()
