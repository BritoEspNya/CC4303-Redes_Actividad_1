import socket
import json
import base64
import os

VM_IP = '127.0.0.1'
PORT = 8000
PORT_SERVER = 80

proxy_name = "Benjas"
recv_buffer = 50
end_of_message = "\n"
proxy_socket_address = (VM_IP, PORT)

base_dir = os.path.dirname(os.path.abspath(__file__))
ruta_json = os.path.join(base_dir, "blocked.json")
ruta_gato = os.path.join(base_dir, "img/forbidden_cat.jpeg")

def receive_full_message(connection_socket, recv_buffer):
    full_header = ""
    full_body = ""
    
    recv_message = connection_socket.recv(recv_buffer)
    full_message = recv_message

    # Get headers
    end_of_header = "\r\n\r\n"
    while not end_of_header in recv_message.decode():
        recv_message = connection_socket.recv(recv_buffer)
        full_message += recv_message
    split_message = full_message.decode().split(end_of_header)
    full_header = split_message[0]

    # Get body if available
    body_length = 0
    headers = full_header.split("\r\n")
    for header in headers:
        if ":" in header:
            split_header = header.split(":")
            header_name = split_header[0]
            header_content = split_header[1]
            if "Content-Length" in header_name:
                body_length = int(header_content)
                full_body = split_message[1].encode()
                break
    while len(full_body) < body_length:
        recv_message = connection_socket.recv(recv_buffer)
        full_body += recv_message
        full_message += recv_message
    
    return full_message
    index = full_message.rfind(end_sequence)
    return full_message[:index]

def parse_HTTP_message(http_message):
    http_split = http_message.split("\r\n\r\n")

    http_header = http_split[0]
    http_content = None

    headers_dict = dict()
    headers = http_header.split("\r\n")
    headers_dict["Start-Line"] = headers[0]
    for header in headers:
        if ":" in header:
            split_header = header.split(":")
            header_name = split_header[0]
            header_content = split_header[1]
            headers_dict[header_name] = header_content

    if len(http_split) > 1:
        http_content = http_split[1]

    return headers_dict, http_content

def create_get_HTTP(host, path):
    status_line = f'GET {path} HTTP/1.1'
    headers = f'Host: {host}\r\nUser-Agent: {VM_IP}:{PORT}\r\nAccept: */*\r\nConnection: Keep-Alive\r\nX-ElQuePregunta: {proxy_name}'
    full_request = status_line + "\r\n" + headers + "\r\n\r\n"
    return full_request

def create_403_response():
    status_line = "HTTP/1.1 403 Forbidden"
    with open(ruta_gato, "rb") as file:
        img_base64 = base64.b64encode(file.read()).decode()
    body = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Forbidden Page :O</title>
</head>
<body>
    <h1>403 Forbidden</h1>
    <img src="data:image/jpeg;base64,{img_base64}" width="2000" alt="Forbidden Cat">
</body>
</html>
"""
    headers = f'Content-Type: text/html; charset=utf-8\r\nContent_Length: {len(body)}\r\nConnection: close'

    full_response = status_line + "\r\n" + headers + "\r\n\r\n" + body
    return full_response

def create_redacted_response(HTTP_response):
    http_split = HTTP_response.split("\r\n\r\n")
    if len(http_split) > 1:
        response_body = http_split[1]

    status_line = "HTTP/1.1 200 OK"
    redacted_response = response_body
    with open("/blocked.json") as file:
        data = json.load(file)
        for forbidden_word in data.get("forbidden_words"):
            for word, replacement in forbidden_word.items():
                redacted_response = redacted_response.replace(word, replacement)
    headers = f'Content-Type: text/html; charset=utf-8\r\nContent_Length: {len(redacted_response)}\r\nConnection: close'
    
    full_response = status_line + "\r\n" + headers + "\r\n\r\n" + redacted_response
    return full_response

def get_path_from_header(headers):
    path = headers.get("Start-Line").split(" ")[1]
    return path

def get_host_from_header(headers):
    host = headers.get("Host").replace(" ", "")
    return host.replace(" ", "")

def main():
    # Definir socket para conectar con el cliente
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Para testing
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #####

    proxy_socket.bind(proxy_socket_address)
    proxy_socket.listen(3)

    while True:
        # Conexión con el cliente
        client_socket, new_socket_address = proxy_socket.accept()

        recv_message = receive_full_message(client_socket, recv_buffer)

        client_headers, client_body = parse_HTTP_message(recv_message.decode())
        server_host = get_host_from_header(client_headers)
        server_path = get_path_from_header(client_headers)

        response_message = None

        # Revisar si es sitio permitido
        block_site = False
        with open(ruta_json) as file:
            data = json.load(file)
            for blocked_site in data.get("blocked"):
                if blocked_site == server_path:
                    block_site = True
                    break

        # Conexión con servidor
        if not block_site:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            server_socket.connect((server_host, PORT_SERVER))
            
            server_socket.send(create_get_HTTP(server_host, server_path).encode())

            server_response = receive_full_message(server_socket, recv_buffer)

            server_socket.close()

            # Revisar palabras permitidas
            response_message = create_redacted_response(server_response.decode())
        else:
            response_message = create_403_response()

        # Enviar respuesta servidor -> cliente
        client_socket.send(response_message.encode())

        client_socket.close()

if __name__ == "__main__":
    main()