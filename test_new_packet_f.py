from router import parse_packet, create_packet

IP_packet_v1 = b'\x7f\x00\x00\x01"\xb1\xffMessage with ttl 255'
parsed_IP_packet = parse_packet(IP_packet_v1)
IP_packet_v2_str = create_packet(parsed_IP_packet)
IP_packet_v2 = IP_packet_v2_str#.encode()

print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))