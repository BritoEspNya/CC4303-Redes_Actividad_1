import socket
import sys
from router import create_packet

def send_message(IP_router_final: str,
                 Port_router_final: int,
                 IP_router_to_send: str,
                 Port_router_to_send: int,
                 TTL_of_packet: int,
                 message: str) -> None:
    
    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    parsed_IP_packet = {
        "address": IP_router_final,
        "port": Port_router_final,
        "ttl": TTL_of_packet,
        "msg": message
    }
    packet = create_packet(parsed_IP_packet)

    try:
        socket_udp.sendto(packet, (IP_router_to_send, Port_router_to_send))
    finally:
        socket_udp.close()

def main():
    if len(sys.argv) < 7: # Expected: client.py IP_router_final Port_router_final IP_router_to_send Port_router_to_send TTL_of_packet message
        sys.exit(1)

    IP_router_final = sys.argv[1]
    Port_router_final = int(sys.argv[2])
    IP_router_to_send = sys.argv[3]
    Port_router_to_send = int(sys.argv[4])
    TTL_of_packet = int(sys.argv[5])
    message = sys.argv[6]

    send_message(IP_router_final, Port_router_final, IP_router_to_send, Port_router_to_send, TTL_of_packet, message)

if __name__ == "__main__":
    main()