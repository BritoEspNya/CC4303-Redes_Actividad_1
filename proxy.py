import socket
import json

VM_IP = '127.0.0.1'
PORT = 8000
PORT_SERVER = 80

proxy_name = "Benjas"
buff_size = 1024
end_of_message = "\n"
proxy_socket_address = (VM_IP, PORT)

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

def create_get_HTTP(site):
    status_line = f'GET / HTTP/1.1'
    headers = f'Host: {site}\r\nUser-Agent: {VM_IP}:{PORT}\r\nAccept: */*\r\nConnection: Keep-Alive\r\nX-ElQuePregunta: {proxy_name}'
    full_request = status_line + "\r\n" + headers + "\r\n\r\n"
    return full_request

def create_403_response():
    status_line = "HTTP/1.1 403 Forbidden"
    body = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Forbidden Page :O</title>
</head>
<body>
    <h1>403 Forbidden</h1>
    <img src="/img/forbidden_cat.jpeg" alt="Forbidden Cat">
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
    with open("blocked.json") as file:
        data = json.load(file)
        for forbidden_word in data.get("forbidden_words"):
            for word, replacement in forbidden_word.items():
                redacted_response = redacted_response.replace(word, replacement)
    headers = f'Content-Type: text/html; charset=utf-8\r\nContent_Length: {len(redacted_response)}\r\nConnection: close'
    
    full_response = status_line + "\r\n" + headers + "\r\n\r\n" + redacted_response
    return full_response

def main():
    # Definir socket para conectar con el cliente
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(proxy_socket_address)
    proxy_socket.listen(3)

    while True:
        # Conexión con el cliente
        client_socket, new_socket_address = proxy_socket.accept()

        recv_message = receive_full_message(client_socket, buff_size, end_of_message)

        client_headers, client_body = parse_HTTP_message(recv_message)

        site = (client_headers.get("Host", None)).replace(" ", "")
        response_message = None

        # Revisar si es sitio permitido
        block_site = False
        with open("blocked.json") as file:
            data = json.load(file)
            for blocked_site in data.get("blocked"):
                if blocked_site.replace("http://", "") == site:
                    block_site = True
                    break

        # Conexión con servidor
        if not block_site:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((site.replace(" ", ""), PORT_SERVER))

            server_socket.send(create_get_HTTP(site).encode())

            server_response = server_socket.recv(buff_size)

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