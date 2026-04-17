import socket
import json

VM_IP = '127.0.0.1'
PORT = 8000

def parse_HTTP_message(http_message):
    http_split = http_message.split("\r\n\r\n")

    http_header = http_split[0]
    http_content = None

    headers = http_header.split("\r\n")
    headers_dict = dict()
    headers_dict["Start-Line"] = headers[0]
    for header in headers:
        if ":" in header:
            split_header = header.split(":")
            header_name = split_header[0]
            header_content = split_header[1]
            headers_dict[header_name] = header_content
        else: print(header)

    headers_json = json.dumps(headers_dict)

    if len(http_split) > 1:
        http_content = http_split[1]

    return headers_json, http_content

def create_HTTP_message(client_name):
    status_line = "HTTP/1.1 200 OK\r\n"
    body = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Server Response</title>
</head>
<body>
    <h1>Server Response</h1>
    <h3>owo</h3>
</body>
</html>
"""
    headers = f"Content-Type: text/html; charset=utf-8\r\nContent-Length: {len(body)}\r\nX-ElQuePregunta: {client_name}\r\n"
    blank_line = "\r\n"
    
    full_response = status_line + headers + blank_line + body

    return full_response

def receive_full_message(connection_socket, buff_size, end_sequence):
    recv_message = connection_socket.recv(buff_size)
    full_message = recv_message

    is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    while not is_end_of_message:
        recv_message = connection_socket.recv(buff_size)
        full_message += recv_message
        is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    full_message = remove_end_of_message(full_message.decode(), end_sequence)

    return full_message


def contains_end_of_message(message, end_sequence):
    return message.endswith(end_sequence)


def remove_end_of_message(full_message, end_sequence):
    index = full_message.rfind(end_sequence)
    return full_message[:index]

buff_size = 1024
end_of_message = "\n"
new_socket_address = (VM_IP, PORT)

def main(new_socket_address, config_name="config", config_json=None):
    with open(config_json) as file:
        data = json.load(file)
        server_name = data.get("name")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.bind(new_socket_address)

    server_socket.listen(3)

    while True:
        new_socket, new_socket_address = server_socket.accept()

        recv_message = receive_full_message(new_socket, buff_size, end_of_message)

        http_headers_json_str, http_content = parse_HTTP_message(recv_message)
        print(http_headers_json_str)

        #http_headers_json = json.loads(http_headers_json_str)

        response_message = create_HTTP_message(server_name)
        new_socket.send(response_message.encode('utf-8'))

        new_socket.close()
        print(f"conexión con {new_socket_address} ha sido cerrada")

config_json = "config.json"
config_name = "config"

main(new_socket_address, config_name, config_json)