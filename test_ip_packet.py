def parse_packet(IP_packet: bytes) -> dict:
    # Decode address
    address = ".".join(str(octet) for octet in IP_packet[:4])

    # Decode port
    port = str(IP_packet[4])

    # Decode message
    msg = IP_packet[5:].decode("utf-8")

    parsed_packet = {
        "address": address,
        "port": port,
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
    port_bytes = int(parsed_IP_packet["port"]).to_bytes(1)

    # Encode message
    msg_bytes = parsed_IP_packet["msg"].encode('utf-8')

    packet = b''.join([address_bytes, port_bytes, msg_bytes])

    return packet

# Paquete: 127.0.0.1 255 Hola mundo!
IP_packet_v1 = b'\x7f\x00\x00\x01\xffHola mundo!'
parsed_IP_packet = parse_packet(IP_packet_v1)
IP_packet_v2 = create_packet(parsed_IP_packet)
print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))