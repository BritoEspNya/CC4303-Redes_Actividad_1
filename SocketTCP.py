import random
import socket
import time


class SocketTCP:
    def __init__(self):
        # Recursos para la comunicación
        self.socket = None
        self.local_address = None
        self.remote_address = None
        self.sequence_number = None
        self.expected_sequence = None
        self.timeout = 0.5
        self.max_payload = 16
        self.estado = "CLOSED"
        self._pending_datagram = None

    def _recv_datagram(self):
        if self._pending_datagram is not None:
            pending = self._pending_datagram
            self._pending_datagram = None
            return pending

        data, sender = self.socket.recvfrom(4096)
        return data, sender

    def _ensure_socket(self):
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.timeout)

    def bind(self, address):
        self._ensure_socket()
        self.socket.bind(address)
        self.local_address = self.socket.getsockname()
        self.estado = "LISTEN"

    def connect(self, address):
        self._ensure_socket()
        if self.local_address is None:
            self.socket.bind(("localhost", 0))
            self.local_address = self.socket.getsockname()

        # Resolver hostname a IP para evitar discrepancias ('localhost' vs '127.0.0.1')
        host, port = address
        try:
            remote_ip = socket.gethostbyname(host)
        except Exception:
            remote_ip = host
        self.remote_address = (remote_ip, port)
        self.sequence_number = random.randint(0, 100)

        syn_segment = self.create_segment(syn=1, seq=self.sequence_number)
        syn_bytes = syn_segment.encode("latin-1")

        while True:
            # cliente: enviar SYN
            print(f"SYN enviado -> seq={self.sequence_number} to {self.remote_address}")
            self.socket.sendto(syn_bytes, self.remote_address)
            try:
                data, sender = self.socket.recvfrom(4096)
            except socket.timeout:
                continue

            # aceptar SYN-ACK incluso si viene de un puerto distinto (servidor puede responder desde otro socket)
            segment = self.parse_segment(data.decode("latin-1"))
            if segment["syn"] == 1 and segment["ack"] == 1:
                print(f"SYN-ACK recibido <- seq={segment['seq']} from {sender}")
                # actualizar remote_address al remitente real (puerto efímero del servidor)
                self.remote_address = sender
                self.sequence_number += 1
                ack_segment = self.create_segment(ack=1, seq=self.sequence_number)
                self.socket.sendto(ack_segment.encode("latin-1"), self.remote_address)
                print(f"ACK enviado -> seq={self.sequence_number} to {self.remote_address}")
                self.estado = "ESTABLISHED"
                return

    def accept(self):
        self._ensure_socket()

        while True:
            try:
                data, sender = self.socket.recvfrom(4096)
            except socket.timeout:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except (UnicodeDecodeError, ValueError, KeyError):
                continue

            if segment["syn"] != 1 or segment["ack"] != 0:
                continue

            connection = SocketTCP()
            connection._ensure_socket()
            connection.socket.bind((self.local_address[0], 0))
            connection.local_address = connection.socket.getsockname()
            connection.remote_address = sender
            connection.sequence_number = random.randint(0, 100)
            connection.expected_sequence = segment["seq"] + 1
            connection.estado = "SYN-RECEIVED"
            print(f"SYN recibido <- seq={segment['seq']} from {sender}")
            synack_segment = connection.create_segment(
                syn=1,
                ack=1,
                seq=connection.sequence_number,
            )
            connection.socket.sendto(synack_segment.encode("latin-1"), sender)
            print(f"SYN-ACK enviado -> seq={connection.sequence_number} to {sender}")

            while True:
                try:
                    ack_data, ack_sender = connection._recv_datagram()
                except socket.timeout:
                    connection.socket.sendto(synack_segment.encode("latin-1"), sender)
                    continue

                if ack_sender != sender:
                    continue

                try:
                    ack_segment = self.parse_segment(ack_data.decode("latin-1"))
                except (UnicodeDecodeError, ValueError, KeyError):
                    continue

                if ack_segment["ack"] == 1:
                    print(f"ACK recibido <- seq={ack_segment['seq']} from {ack_sender}")
                    connection.sequence_number += 1
                    connection.estado = "ESTABLISHED"
                    return connection, connection.local_address

                if ack_segment["syn"] == 0 and ack_segment["ack"] == 0 and ack_segment["fin"] == 0:
                    # Caso borde: se perdió el ACK final y el primer segmento de datos
                    # llega antes de que accept() termine. Lo guardamos para recv().
                    connection._pending_datagram = (ack_data, ack_sender)
                    print(f"Datos recibidos durante handshake desde {ack_sender}, handshake completado implícitamente")
                    connection.sequence_number += 1
                    connection.estado = "ESTABLISHED"
                    return connection, connection.local_address

                # Cualquier otro paquete se ignora y se sigue esperando.
                continue

    def send_segment(self, segment_str):
        if self.socket is None or self.remote_address is None:
            raise OSError("socket no conectado")
        self.socket.sendto(segment_str.encode("latin-1"), self.remote_address)

    def recv_segment(self):
        if self.socket is None:
            raise OSError("socket no inicializado")

        try:
            data, sender = self._recv_datagram()
        except socket.timeout:
            return None, None

        try:
            segment = self.parse_segment(data.decode("latin-1"))
        except (UnicodeDecodeError, ValueError, KeyError):
            return None, sender

        return segment, sender

    def send(self, message: bytes) -> int:
        """Enviar mensaje usando Stop & Wait.

        El primer segmento transmite el largo total del mensaje (en bytes).
        Luego se envían los chunks de a lo más self.max_payload bytes, esperando
        un ACK por cada segmento y retransmitiendo si ocurre timeout.
        """
        if self.socket is None or self.remote_address is None:
            raise OSError("socket no conectado")

        if isinstance(message, str):
            payload = message.encode("latin-1")
        else:
            payload = bytes(message)

        total_sent = 0
        message_length = len(payload)

        # primer segmento: informar largo
        seq = self.sequence_number if self.sequence_number is not None else 0
        length_segment = self.create_segment(syn=0, ack=0, fin=0, seq=seq, data=str(message_length))
        length_bytes = length_segment.encode("latin-1")

        # enviar y esperar ACK
        while True:
            self.socket.sendto(length_bytes, self.remote_address)
            try:
                data, sender = self.socket.recvfrom(4096)
            except socket.timeout:
                continue

            try:
                seg = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            if seg.get("ack") == 1 and seg.get("seq") == seq:
                break

        # Secuencia de datos por mensaje: se reinicia en 0 para evitar arrastre
        # entre mensajes consecutivos.
        data_seq = 0

        # enviar chunks con Stop & Wait
        offset = 0
        while offset < message_length:
            chunk = payload[offset : offset + self.max_payload]
            chunk_str = chunk.decode("latin-1")
            seg_str = self.create_segment(syn=0, ack=0, fin=0, seq=data_seq, data=chunk_str)
            seg_bytes = seg_str.encode("latin-1")

            while True:
                self.socket.sendto(seg_bytes, self.remote_address)
                try:
                    data, sender = self.socket.recvfrom(4096)
                except socket.timeout:
                    continue

                try:
                    ack = self.parse_segment(data.decode("latin-1"))
                except Exception:
                    continue

                if ack.get("ack") == 1 and ack.get("seq") == data_seq:
                    break

            total_sent += len(chunk)
            offset += len(chunk)
            data_seq += 1

        # mantener avance de secuencia de conexión solo para el próximo length-seg
        self.sequence_number = seq + 1

        return total_sent

    def recv(self, buff_size: int) -> bytes:
        """Recibir mensaje usando Stop & Wait.

        El primer segmento recibido contiene el largo total del mensaje (en bytes).
        La función devuelve como máximo `buff_size` bytes. Si el mensaje es más
        largo, puede llamarse nuevamente hasta recibir todo.
        """
        if self.socket is None:
            raise OSError("socket no inicializado")

        # inicializar estructuras de recepción si es necesario
        if not hasattr(self, "_recv_total_len") or self._recv_total_len is None:
            self._recv_total_len = 0
        if not hasattr(self, "_recv_buffer"):
            self._recv_buffer = bytearray()
        if not hasattr(self, "_recv_expected_seq"):
            self._recv_expected_seq = None
        if not hasattr(self, "_recv_bytes_delivered"):
            self._recv_bytes_delivered = 0
        if not hasattr(self, "_recv_length_seq"):
            self._recv_length_seq = None
        if not hasattr(self, "_recv_next_length_seq"):
            self._recv_next_length_seq = None

        # si no sabemos el total, esperar segmento inicial con el largo
        while self._recv_total_len == 0:
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                continue

            try:
                seg = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            # Si ya conocemos qué secuencia debe tener el próximo length-seg,
            # ignoramos cualquier otro paquete pendiente que pertenezca al mensaje anterior.
            if self._recv_next_length_seq is not None and seg.get("seq") != self._recv_next_length_seq:
                continue

            # primer segmento con el largo
            try:
                msg_len = int(seg.get("data", "0"))
            except Exception:
                continue

            self._recv_total_len = msg_len
            self._recv_length_seq = seg.get("seq")
            self._recv_expected_seq = 0
            self.remote_address = sender
            self._recv_bytes_delivered = 0
            self._recv_buffer = bytearray()

            print(f"[recv] length-seg received seq={seg.get('seq')} len={self._recv_total_len} from {sender}")
            # enviar ACK del length segment
            ack_seg = self.create_segment(ack=1, seq=seg.get("seq"))
            self.socket.sendto(ack_seg.encode("latin-1"), sender)

        # ahora recibir datos hasta llenar al menos la cantidad restante: min(remaining, buff_size)
        remaining = self._recv_total_len - self._recv_bytes_delivered
        target = min(remaining, buff_size)
        while len(self._recv_buffer) < target:
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                continue

            try:
                seg = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            # aceptar solo si viene del mismo remitente
            if sender != self.remote_address:
                continue

            # si el emisor retransmite el segmento de largo porque se perdió su ACK,
            # reenviamos el ACK correspondiente y seguimos esperando datos.
            if self._recv_length_seq is not None and seg.get("seq") == self._recv_length_seq:
                ack_seg = self.create_segment(ack=1, seq=self._recv_length_seq)
                self.socket.sendto(ack_seg.encode("latin-1"), sender)
                continue

            # aceptar solo si tiene la secuencia esperada
            if seg.get("seq") != self._recv_expected_seq:
                # si llega duplicado, reenviar ack del último aceptado
                last_ack_seq = self._recv_expected_seq - 1 if self._recv_expected_seq is not None else seg.get("seq")
                ack_seg = self.create_segment(ack=1, seq=last_ack_seq)
                self.socket.sendto(ack_seg.encode("latin-1"), sender)
                continue

            # añadir datos
            data_bytes = seg.get("data", "").encode("latin-1")
            print(f"[recv] data-seg received seq={seg.get('seq')} len={len(data_bytes)}")
            self._recv_buffer.extend(data_bytes)
            self._recv_expected_seq = seg.get("seq") + 1

            # enviar ACK
            ack_seg = self.create_segment(ack=1, seq=seg.get("seq"))
            self.socket.sendto(ack_seg.encode("latin-1"), sender)

        # devolver hasta buff_size bytes (pero no más que lo que tenemos en buffer)
        out = bytes(self._recv_buffer[:min(len(self._recv_buffer), buff_size)])
        del self._recv_buffer[:len(out)]
        self._recv_bytes_delivered += len(out)

        # si ya entregamos todo el mensaje, resetear estado
        if self._recv_total_len != 0 and self._recv_bytes_delivered >= self._recv_total_len:
            last_length_seq = self._recv_length_seq
            self._recv_total_len = 0
            self._recv_length_seq = None
            self._recv_expected_seq = None
            self._recv_buffer = bytearray()
            self._recv_bytes_delivered = 0
            if last_length_seq is not None:
                self._recv_next_length_seq = last_length_seq + 1

        return out

    def close(self):
        """Cierre activo de conexión (lado Host A)."""
        if self.socket is None or self.remote_address is None:
            raise OSError("socket no conectado")

        fin_seq = self.sequence_number if self.sequence_number is not None else 0
        fin_segment = self.create_segment(fin=1, seq=fin_seq)
        fin_bytes = fin_segment.encode("latin-1")

        self.estado = "FIN-WAIT-1"
        timeout_count = 0

        # 1) enviar FIN y esperar ACK
        while timeout_count < 3:
            print(f"FIN enviado -> seq={fin_seq} to {self.remote_address}")
            self.socket.sendto(fin_bytes, self.remote_address)
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                timeout_count += 1
                continue

            if sender != self.remote_address:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except (UnicodeDecodeError, ValueError, KeyError):
                continue

            if segment["ack"] == 1 and segment["seq"] == fin_seq:
                print(f"ACK de FIN recibido <- seq={segment['seq']} from {sender}")
                self.sequence_number = fin_seq + 1
                break

        if timeout_count >= 3:
            self.estado = "CLOSED"
            if self.socket is not None:
                self.socket.close()
            self.socket = None
            self.remote_address = None
            return

        self.estado = "FIN-WAIT-2"
        timeout_count = 0

        # 2) esperar FIN del otro lado y responder ACK
        while timeout_count < 3:
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                timeout_count += 1
                continue

            if sender != self.remote_address:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except (UnicodeDecodeError, ValueError, KeyError):
                continue

            if segment["fin"] == 1:
                print(f"FIN recibido <- seq={segment['seq']} from {sender}")
                ack_seq = segment["seq"]
                ack_segment = self.create_segment(ack=1, seq=ack_seq)
                ack_bytes = ack_segment.encode("latin-1")
                for _ in range(3):
                    self.socket.sendto(ack_bytes, self.remote_address)
                    print(f"ACK de FIN enviado -> seq={ack_seq} to {self.remote_address}")
                    time.sleep(self.timeout)
                break

        if timeout_count >= 3:
            self.estado = "CLOSED"
            if self.socket is not None:
                self.socket.close()
            self.socket = None
            self.remote_address = None
            return

        self.estado = "CLOSED"
        if self.socket is not None:
            self.socket.close()
        self.socket = None
        self.remote_address = None

    def recv_close(self):
        """Cierre pasivo de conexión (lado Host B)."""
        if self.socket is None:
            raise OSError("socket no inicializado")

        self.estado = "CLOSE-WAIT"

        # 1) esperar FIN del otro lado y responder ACK
        while True:
            try:
                data, sender = self.socket.recvfrom(4096)
            except socket.timeout:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except (UnicodeDecodeError, ValueError, KeyError):
                continue

            if segment["fin"] != 1:
                continue

            self.remote_address = sender
            print(f"FIN recibido <- seq={segment['seq']} from {sender}")
            ack_segment = self.create_segment(ack=1, seq=segment["seq"])
            self.socket.sendto(ack_segment.encode("latin-1"), sender)
            print(f"ACK de FIN enviado -> seq={segment['seq']} to {sender}")
            break

        # 2) iniciar FIN propio y esperar ACK
        fin_seq = self.sequence_number if self.sequence_number is not None else 0
        fin_segment = self.create_segment(fin=1, seq=fin_seq)
        fin_bytes = fin_segment.encode("latin-1")

        self.estado = "LAST-ACK"
        timeout_count = 0
        while timeout_count < 3:
            print(f"FIN enviado -> seq={fin_seq} to {self.remote_address}")
            self.socket.sendto(fin_bytes, self.remote_address)
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                timeout_count += 1
                continue

            if sender != self.remote_address:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except (UnicodeDecodeError, ValueError, KeyError):
                continue

            if segment["ack"] == 1 and segment["seq"] == fin_seq:
                print(f"ACK de FIN recibido <- seq={segment['seq']} from {sender}")
                self.sequence_number = fin_seq + 1
                break

        if timeout_count >= 3:
            self.estado = "CLOSED"
            if self.socket is not None:
                self.socket.close()
            self.socket = None
            self.remote_address = None
            return

        self.estado = "CLOSED"
        if self.socket is not None:
            self.socket.close()
        self.socket = None
        self.remote_address = None

    @staticmethod
    def parse_segment(segment_str):
        """Convierte un segmento TCP string a una estructura de datos.
        
        Formato: [SYN]|||[ACK]|||[FIN]|||[SEQ]|||[DATOS]
        Retorna un diccionario con las claves: syn, ack, fin, seq, data
        """
        partes = segment_str.split("|||", 4)

        if len(partes) < 4:
            raise ValueError("Segmento mal formado")

        segmento = {
            "syn": int(partes[0]),
            "ack": int(partes[1]),
            "fin": int(partes[2]),
            "seq": int(partes[3]),
            "data": partes[4] if len(partes) > 4 else ""
        }

        return segmento

    @staticmethod
    def create_segment(syn=0, ack=0, fin=0, seq=0, data=""):
        """Crea un segmento TCP a partir de sus componentes.
        
        Retorna un string en formato: [SYN]|||[ACK]|||[FIN]|||[SEQ]|||[DATOS]
        """
        return f"{syn}|||{ack}|||{fin}|||{seq}|||{data}"