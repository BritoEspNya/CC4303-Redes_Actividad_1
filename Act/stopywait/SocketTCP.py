import random
import socket
import time
import base64


class SocketTCP:
    def __init__(self):
        self.socket = None
        self.local_address = None
        self.remote_address = None
        self.sequence_number = None
        self.expected_sequence = None
        self.timeout = 0.5
        self.max_payload = 16
        self.max_retries = 200
        self.estado = "CLOSED"
        self.debug = False

        self._pending_datagram = None
        self._recv_total_len = 0
        self._recv_buffer = bytearray()
        self._recv_expected_seq = None
        self._recv_bytes_delivered = 0
        self._recv_length_seq = None
        self._recv_next_length_seq = None
        self._recv_last_ack_seq = None
        self._recv_last_ack_sender = None

    def set_debug(self, enabled: bool):
        self.debug = bool(enabled)

    def _log(self, message: str):
        if self.debug:
            print(message)

    def _ensure_socket(self):
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.timeout)

    def _recv_datagram(self):
        if self._pending_datagram is not None:
            pending = self._pending_datagram
            self._pending_datagram = None
            return pending
        return self.socket.recvfrom(4096)

    def _send_ack_reliably(self, seq, address, repeats=3):
        ack_bytes = self.create_segment(ack=1, seq=seq).encode("latin-1")
        for _ in range(repeats):
            self.socket.sendto(ack_bytes, address)

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
            self._log(f"SYN enviado -> seq={self.sequence_number} to {self.remote_address}")
            self.socket.sendto(syn_bytes, self.remote_address)
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            if segment["syn"] == 1 and segment["ack"] == 1:
                self._log(f"SYN-ACK recibido <- seq={segment['seq']} from {sender}")
                self.remote_address = sender
                self.sequence_number += 1
                ack_segment = self.create_segment(ack=1, seq=self.sequence_number)
                self.socket.sendto(ack_segment.encode("latin-1"), self.remote_address)
                self._log(f"ACK enviado -> seq={self.sequence_number} to {self.remote_address}")
                self.estado = "ESTABLISHED"
                return

    def accept(self):
        self._ensure_socket()

        while True:
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            if segment["syn"] != 1 or segment["ack"] != 0:
                continue

            connection = SocketTCP()
            connection.set_debug(self.debug)
            connection._ensure_socket()
            connection.socket.bind((self.local_address[0], 0))
            connection.local_address = connection.socket.getsockname()
            connection.remote_address = sender
            connection.sequence_number = random.randint(0, 100)
            connection.expected_sequence = segment["seq"] + 1
            connection.estado = "SYN-RECEIVED"

            connection._log(f"SYN recibido <- seq={segment['seq']} from {sender}")
            synack_segment = connection.create_segment(syn=1, ack=1, seq=connection.sequence_number)
            connection.socket.sendto(synack_segment.encode("latin-1"), sender)
            connection._log(f"SYN-ACK enviado -> seq={connection.sequence_number} to {sender}")

            while True:
                try:
                    ack_data, ack_sender = connection._recv_datagram()
                except socket.timeout:
                    connection.socket.sendto(synack_segment.encode("latin-1"), sender)
                    continue

                if ack_sender != sender:
                    continue

                try:
                    ack_segment = connection.parse_segment(ack_data.decode("latin-1"))
                except Exception:
                    continue

                if ack_segment["ack"] == 1:
                    connection._log(f"ACK recibido <- seq={ack_segment['seq']} from {ack_sender}")
                    connection.sequence_number += 1
                    connection.estado = "ESTABLISHED"
                    return connection, connection.local_address

                if ack_segment["syn"] == 0 and ack_segment["ack"] == 0 and ack_segment["fin"] == 0:
                    connection._pending_datagram = (ack_data, ack_sender)
                    connection._log(
                        f"Datos recibidos durante handshake desde {ack_sender}, handshake completado implícitamente"
                    )
                    connection.sequence_number += 1
                    connection.estado = "ESTABLISHED"
                    return connection, connection.local_address

    def send(self, message: bytes) -> int:
        if self.socket is None or self.remote_address is None:
            raise OSError("socket no conectado")

        payload = message.encode("latin-1") if isinstance(message, str) else bytes(message)
        message_length = len(payload)
        total_sent = 0

        seq = self.sequence_number if self.sequence_number is not None else 0
        length_segment = self.create_segment(seq=seq, data=str(message_length))
        length_bytes = length_segment.encode("latin-1")

        retries = 0
        while True:
            if retries > self.max_retries:
                raise TimeoutError("No se pudo confirmar ACK del segmento de longitud")

            self.socket.sendto(length_bytes, self.remote_address)
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                retries += 1
                self._log(f"[send] timeout esperando ACK length seq={seq}, retry={retries}")
                continue

            if sender != self.remote_address:
                continue

            try:
                ack = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            if ack.get("ack") == 1 and ack.get("seq") == seq:
                self._log(f"[send] ACK length confirmado seq={seq}")
                break

        data_seq = 0
        offset = 0
        while offset < message_length:
            chunk = payload[offset : offset + self.max_payload]
            encoded_chunk = base64.b64encode(chunk).decode("ascii")
            seg = self.create_segment(seq=data_seq, data=encoded_chunk)
            seg_bytes = seg.encode("latin-1")

            retries = 0
            while True:
                if retries > self.max_retries:
                    raise TimeoutError(f"No se pudo confirmar ACK para seq={data_seq}")

                self.socket.sendto(seg_bytes, self.remote_address)
                try:
                    data, sender = self._recv_datagram()
                except socket.timeout:
                    retries += 1
                    self._log(f"[send] timeout esperando ACK data seq={data_seq}, retry={retries}")
                    continue

                if sender != self.remote_address:
                    continue

                try:
                    ack = self.parse_segment(data.decode("latin-1"))
                except Exception:
                    continue

                if ack.get("ack") == 1 and ack.get("seq") == data_seq:
                    self._log(f"[send] ACK data confirmado seq={data_seq}")
                    break

            offset += len(chunk)
            total_sent += len(chunk)
            data_seq += 1

        self.sequence_number = seq + 1
        return total_sent

    def recv(self, buff_size: int) -> bytes:
        if self.socket is None:
            raise OSError("socket no inicializado")

        while self._recv_total_len == 0:
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                continue

            try:
                seg = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            if self._recv_next_length_seq is not None and seg.get("seq") != self._recv_next_length_seq:
                continue

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
            self._recv_last_ack_seq = seg.get("seq")
            self._recv_last_ack_sender = sender

            self._log(f"[recv] length-seg received seq={seg.get('seq')} len={self._recv_total_len} from {sender}")
            self._send_ack_reliably(seg.get("seq"), sender)

        remaining = self._recv_total_len - self._recv_bytes_delivered
        target = min(remaining, buff_size)

        while len(self._recv_buffer) < target:
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                if self._recv_last_ack_seq is not None and self._recv_last_ack_sender is not None:
                    self._send_ack_reliably(self._recv_last_ack_seq, self._recv_last_ack_sender)
                continue

            try:
                seg = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            if sender != self.remote_address:
                continue

            if seg.get("seq") == self._recv_expected_seq:
                try:
                    data_bytes = base64.b64decode(seg.get("data", "").encode("ascii"), validate=True)
                except Exception:
                    continue
                self._log(f"[recv] data-seg received seq={seg.get('seq')} len={len(data_bytes)}")
                self._recv_buffer.extend(data_bytes)
                self._recv_expected_seq = seg.get("seq") + 1
                self._recv_last_ack_seq = seg.get("seq")
                self._recv_last_ack_sender = sender
                self._send_ack_reliably(seg.get("seq"), sender)
                continue

            if (
                self._recv_length_seq is not None
                and seg.get("seq") == self._recv_length_seq
                and seg.get("data") == str(self._recv_total_len)
            ):
                self._send_ack_reliably(self._recv_length_seq, sender, repeats=5)
                continue

            if self._recv_expected_seq == 0 and self._recv_length_seq is not None:
                last_ack_seq = self._recv_length_seq
            else:
                last_ack_seq = self._recv_expected_seq - 1 if self._recv_expected_seq is not None else seg.get("seq")
            self._send_ack_reliably(last_ack_seq, sender)

        out = bytes(self._recv_buffer[: min(len(self._recv_buffer), buff_size)])
        del self._recv_buffer[: len(out)]
        self._recv_bytes_delivered += len(out)

        if self._recv_total_len != 0 and self._recv_bytes_delivered >= self._recv_total_len:
            last_length_seq = self._recv_length_seq
            self._recv_total_len = 0
            self._recv_length_seq = None
            self._recv_expected_seq = None
            self._recv_buffer = bytearray()
            self._recv_bytes_delivered = 0
            self._recv_last_ack_seq = None
            self._recv_last_ack_sender = None
            if last_length_seq is not None:
                self._recv_next_length_seq = last_length_seq + 1

        return out

    def close(self):
        if self.socket is None or self.remote_address is None:
            raise OSError("socket no conectado")

        fin_seq = self.sequence_number if self.sequence_number is not None else 0
        fin_segment = self.create_segment(fin=1, seq=fin_seq)
        fin_bytes = fin_segment.encode("latin-1")

        self.estado = "FIN-WAIT-1"
        timeout_count = 0

        while timeout_count < 3:
            self._log(f"FIN enviado -> seq={fin_seq} to {self.remote_address}")
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
            except Exception:
                continue

            if segment.get("ack") == 1 and segment.get("seq") == fin_seq:
                self._log(f"ACK de FIN recibido <- seq={segment['seq']} from {sender}")
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
            except Exception:
                continue

            if segment.get("fin") == 1:
                self._log(f"FIN recibido <- seq={segment['seq']} from {sender}")
                ack_seq = segment["seq"]
                ack_bytes = self.create_segment(ack=1, seq=ack_seq).encode("latin-1")
                for _ in range(3):
                    self.socket.sendto(ack_bytes, self.remote_address)
                    self._log(f"ACK de FIN enviado -> seq={ack_seq} to {self.remote_address}")
                    time.sleep(self.timeout)
                break

        self.estado = "CLOSED"
        if self.socket is not None:
            self.socket.close()
        self.socket = None
        self.remote_address = None

    def recv_close(self):
        if self.socket is None:
            raise OSError("socket no inicializado")

        self.estado = "CLOSE-WAIT"

        while True:
            try:
                data, sender = self._recv_datagram()
            except socket.timeout:
                continue

            try:
                segment = self.parse_segment(data.decode("latin-1"))
            except Exception:
                continue

            if segment.get("fin") != 1:
                continue

            self.remote_address = sender
            self._log(f"FIN recibido <- seq={segment['seq']} from {sender}")
            self._send_ack_reliably(segment["seq"], sender)
            self._log(f"ACK de FIN enviado -> seq={segment['seq']} to {sender}")
            break

        fin_seq = self.sequence_number if self.sequence_number is not None else 0
        fin_bytes = self.create_segment(fin=1, seq=fin_seq).encode("latin-1")

        self.estado = "LAST-ACK"
        timeout_count = 0
        while timeout_count < 3:
            self._log(f"FIN enviado -> seq={fin_seq} to {self.remote_address}")
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
            except Exception:
                continue

            if segment.get("ack") == 1 and segment.get("seq") == fin_seq:
                self._log(f"ACK de FIN recibido <- seq={segment['seq']} from {sender}")
                self.sequence_number = fin_seq + 1
                break

        self.estado = "CLOSED"
        if self.socket is not None:
            self.socket.close()
        self.socket = None
        self.remote_address = None

    @staticmethod
    def parse_segment(segment_str):
        
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
        
        return f"{syn}|||{ack}|||{fin}|||{seq}|||{data}"
