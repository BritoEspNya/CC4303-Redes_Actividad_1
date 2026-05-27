import SocketTCP

address = ("localhost", 8000)

client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.connect(address)
print("Client connected to", address)

# test 1
message = "Mensje de len=16".encode()
client_socketTCP.send(message)
print("Test 1 sent")

# test 2
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)
print("Test 2 sent")

# test 3
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)
print("Test 3 sent")

client_socketTCP.close()
print("Client connection closed")
