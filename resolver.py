import socket
import binascii
from pprint import pprint
from collections import Counter

from dnslib import DNSRecord, DNSError
from dnslib.dns import QTYPE, CLASS

VM_IP = '127.0.0.1'
PORT = 8000
ROOT_DNS_IP = '192.33.4.12'
DNS_PORT = 53
DNS_BUFFER_SIZE = 65535
DNS_TIMEOUT = 3.0

# Caché: almacena respuestas DNS por dominio
cache = {}
# Historial: últimas 20 consultas (almacena qname)
query_history = []
MAX_HISTORY = 20
CACHE_SIZE = 3


def update_cache(qname):
	"""Actualiza el caché manteniendo los 3 dominios más frecuentes de las últimas 20 consultas."""
	global query_history, cache
	
	query_history.append(qname)
	if len(query_history) > MAX_HISTORY:
		query_history.pop(0)
	
	# Contar frecuencias
	frecuencias = Counter(query_history)
	
	# Mantener solo los CACHE_SIZE dominios más frecuentes
	top_dominios = frecuencias.most_common(CACHE_SIZE)
	nuevo_cache = {}
	for dominio, _ in top_dominios:
		if dominio in cache:
			nuevo_cache[dominio] = cache[dominio]
	cache = nuevo_cache


def rr_to_dict(rr):
	"""Transforma un RR de dnslib en un diccionario simple."""
	return {
		"name": str(rr.rname),
		"type": QTYPE.get(rr.rtype),
		"class": CLASS.get(rr.rclass),
		"ttl": rr.ttl,
		"rdata": str(rr.rdata),
	}


def parse_dns_message(raw_message):
	"""
	Parsea un mensaje DNS en bytes y retorna una estructura manejable.
	Incluye Qname, ANCOUNT, NSCOUNT, ARCOUNT, y secciones Answer/Authority/Additional.
	"""
	try:
		record = DNSRecord.parse(raw_message)
	except DNSError as e:
		return {
			"error": f"Mensaje DNS invalido: {e}",
			"raw_hex": binascii.hexlify(raw_message).decode("ascii"),
		}

	qname = None
	if record.questions:
		qname = str(record.questions[0].qname)

	parsed_dns = {
		"Qname": qname,
		"ANCOUNT": record.header.a,
		"NSCOUNT": record.header.auth,
		"ARCOUNT": record.header.ar,
		"Answer": [rr_to_dict(rr) for rr in record.rr],
		"Authority": [rr_to_dict(rr) for rr in record.auth],
		"Additional": [rr_to_dict(rr) for rr in record.ar],
		"raw_hex": binascii.hexlify(raw_message).decode("ascii"),
	}

	return parsed_dns


def send_dns_message(message_bytes, server_ip, server_port=DNS_PORT):
	"""Envía un mensaje DNS y retorna la respuesta en bytes, o None si falla."""
	server_address = (server_ip, server_port)
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.settimeout(DNS_TIMEOUT)
	try:
		sock.sendto(message_bytes, server_address)
		response, _ = sock.recvfrom(DNS_BUFFER_SIZE)
		return response
	except (socket.timeout, OSError):
		return None
	finally:
		sock.close()


def extract_first_a_record(records):
	for record in records:
		if record.rtype == QTYPE.A:
			return str(record.rdata)
	return None


def extract_first_ns_record(records):
	for record in records:
		if record.rtype == QTYPE.NS:
			return str(record.rdata)
	return None


def resolver(mensaje_consulta, visitados=None, debug=True):
	"""
	Resuelve iterativamente una consulta DNS en bytes.
	Retorna el mensaje DNS final en bytes si obtiene una respuesta A,
	o b'' si no puede resolverla.
	"""
	es_consulta_raiz = visitados is None
	if visitados is None:
		visitados = set()

	try:
		query_record = DNSRecord.parse(mensaje_consulta)
		qname = str(query_record.questions[0].qname) if query_record.questions else "desconocido"
	except DNSError:
		qname = "desconocido"

	# Verificar caché solo en la consulta raíz
	if es_consulta_raiz and qname in cache:
		if debug:
			print(f"(debug) Consultando '{qname}' (desde CACHÉ)")
		update_cache(qname)
		# Reemplazar el ID de la respuesta cacheada con el ID de la consulta actual
		query_id = mensaje_consulta[:2]
		cached_response = cache[qname]
		respuesta_con_id_correcto = query_id + cached_response[2:]
		return respuesta_con_id_correcto

	consulta_actual = mensaje_consulta
	servidor_actual = ROOT_DNS_IP
	servidor_nombre = "."  # El servidor raíz se denota como '.'

	while True:
		if debug:
			print(f"(debug) Consultando '{qname}' a '{servidor_nombre}' con dirección IP '{servidor_actual}'")
		respuesta = send_dns_message(consulta_actual, servidor_actual)
		if not respuesta:
			return b''

		try:
			record = DNSRecord.parse(respuesta)
		except DNSError:
			return b''

		if extract_first_a_record(record.rr) is not None:
			# Si es la consulta raíz, guardar en caché y actualizar historial
			if es_consulta_raiz:
				cache[qname] = respuesta
				update_cache(qname)
			return respuesta

		ns_name = extract_first_ns_record(record.auth)
		if ns_name is None:
			return b''

		additional_ip = extract_first_a_record(record.ar)
		if additional_ip is not None:
			servidor_actual = additional_ip
			continue

		if ns_name in visitados:
			return b''
		visitados.add(ns_name)

		ns_query = DNSRecord.question(ns_name)
		ns_response = resolver(ns_query.pack(), visitados, debug)
		if not ns_response:
			return b''

		try:
			ns_record = DNSRecord.parse(ns_response)
		except DNSError:
			return b''

		ns_ip = extract_first_a_record(ns_record.rr)
		if ns_ip is None:
			return b''

		servidor_actual = ns_ip
		servidor_nombre = ns_name


def main():
	# UDP is connectionless (no orientado a conexion).
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind((VM_IP, PORT))

	print(f"Escuchando mensajes DNS UDP en {(VM_IP, PORT)}")

	while True:
		data, addr = sock.recvfrom(65535)
		print(f"Recibido desde {addr}: {data}")
		parsed = parse_dns_message(data)
		pprint(parsed)

		respuesta = resolver(data)
		if respuesta:
			sock.sendto(respuesta, addr)
			print(f"Respuesta enviada a {addr}")
		else:
			print("No se pudo resolver la consulta")


if __name__ == "__main__":
	main()

