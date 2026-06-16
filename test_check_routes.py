from router import check_routes    

routes_file_names = ["rutas_R1_v2.txt", "rutas_R2_v2.txt", "rutas_R3_v2.txt"]
test_addresses = [
    ("127.0.0.1", 8881),
    ("127.0.0.1", 8882),
    ("127.0.0.1", 8883),
    ("127.0.0.1", 8884)
]

for file_name in routes_file_names:
    print(f"\nTesting {file_name} for...")
    for test_address in test_addresses:
        print(f"Address: {test_address}, check_routes returned: {check_routes(file_name, test_address)}")