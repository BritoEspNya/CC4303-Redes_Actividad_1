class RouteHandler:
    def __init__(self, router_routes_filename: str):
        self.routes: dict[tuple[str, int, int], list[tuple[str, int]]] = {}
        self.tested_address: dict[tuple[str, int], int] = {}
        self._load_routes(router_routes_filename)
    
    def _load_routes(self, router_routes_filename: str):
        with open(router_routes_filename, "r") as routes_file:
            for line in routes_file:
                segments = line.strip().split(' ')
                address_interval = (segments[0].split("/")[0] ,int(segments[1]), int(segments[2]))
                next_hop_ip = segments[3]
                next_hop_port = int(segments[4])

                if self.routes.get(address_interval) is None:
                    self.routes[address_interval] = [(next_hop_ip, next_hop_port)]
                else:
                    self.routes.get(address_interval).append((next_hop_ip, next_hop_port))
    
    def get_routes_amount(self, destination_address: tuple[str, int]) -> int:
        ammount: int = 0
        for route in self.routes:
            if destination_address[0] == route[0] and destination_address[1] >= route[1] and destination_address[1] <= route[2]:
                ammount += len(self.routes[route])
        return ammount
    
    def check_routes(self, destination_address: tuple[str, int]) -> tuple[str, int]:
        tries_made = self.tested_address.get(destination_address, 0)
        route_ammount = self.get_routes_amount(destination_address)
        if tries_made == route_ammount or tries_made == 0:
            self.tested_address[destination_address] = 0
        
        tries = self.tested_address.get(destination_address)
        for route in self.routes:
            if destination_address[0] == route[0] and destination_address[1] >= route[1] and destination_address[1] <= route[2]:
                for forward_address in self.routes.get(route):
                    if tries == 0:
                        next_hop_ip = forward_address[0]
                        next_hop_port = forward_address[1]
                        self.tested_address[destination_address] += 1
                        return (next_hop_ip, next_hop_port)
                    else:
                        tries -= 1
        
        return (None, None)
                


