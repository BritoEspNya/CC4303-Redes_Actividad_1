## Informe Resolver DNS

Se crea un Socket No orientado a Conexion...
Al correrlo de manera primitiva nos da esta respuesta (no parseada):

```text
b'\x1b\x07\x01 \x00\x01\x00\x00\x00\x00\x00\x01\x07example\x03com\x00\x00\x01\x00\x01\x00\x00)\x04\xd0\x00\x00\x00\x00\x00\x0c\x00\n\x00\x08Sm~\xad\x1b\x96\x9a^'
```

Y el connection timed out por el otro lado.

Luego al crear el parser recolectamos los datos y la guardamos en una estructura que se ve asi:

```text
{'ANCOUNT': 0,
 'ARCOUNT': 1,
 'Additional': [{'class': '1232',
                 'name': '.',
                 'rdata': "[<EDNS Option: Code=10 Data='372a14e92d7803b4'>]",
                 'ttl': 0,
                 'type': 'OPT'}],
 'Answer': [],
 'Authority': [],
 'NSCOUNT': 0,
 'Qname': 'example.com.',
 'raw_hex': '9a8001200001000000000001076578616d706c6503636f6d000001000100002904d000000000000c000a0008372a14e92d7803b4'}
```

 Guardando los datos recomendados y algo mas.

 Finalmente para probar el resolver en primera instancia vemos con www.uchile.cl y comparamos el 8.8.8.8 con el nuestro.
 8.8.8.8: 

```text
 ; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> @8.8.8.8 www.uchile.cl
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 5908
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 512
;; QUESTION SECTION:
;www.uchile.cl.                 IN      A

;; ANSWER SECTION:
www.uchile.cl.          196     IN      A       200.89.76.36

;; Query time: 16 msec
;; SERVER: 8.8.8.8#53(8.8.8.8) (UDP)
;; WHEN: Fri Apr 17 00:10:19 -04 2026
;; MSG SIZE  rcvd: 58
```

Nuestro resolver:

```text
; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> -p8000 @127.0.0.1 www.uchile.cl
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 2868
;; flags: qr aa rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
;; WARNING: recursion requested but not available

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 512
; COOKIE: 2e9bfae89af7cc710100000069e1b2d73c772ff8d6b7be7d (good)
;; QUESTION SECTION:
;www.uchile.cl.                 IN      A

;; ANSWER SECTION:
www.uchile.cl.          300     IN      A       200.89.76.36

;; Query time: 200 msec
;; SERVER: 127.0.0.1#8000(127.0.0.1) (UDP)
;; WHEN: Fri Apr 17 00:11:03 -04 2026
;; MSG SIZE  rcvd: 86
```

Vemos un question y answer similares y llegan a la misma IP: 200.89.76.36
Luego con el modo DEBUG al consultar por www.uchile.cl aparece asi:

```text
(debug) Consultando 'www.uchile.cl.' a '.' con dirección IP '192.33.4.12'
(debug) Consultando 'www.uchile.cl.' a 'c.nic.cl.' con dirección IP '185.159.198.56'
(debug) Consultando 'www.uchile.cl.' a 'ns1.uchile.cl.' con dirección IP '200.89.70.3'
```

Finalmente al preguntar Con el Cache por el mismo dominio:

```text
(debug) Consultando 'www.uchile.cl.' (desde CACHÉ)
```

Tiene un qtime de 4msec contra 244msec de la consulta anterior.

## Pruebas:
- 1 El comando dig -p8000 @IP_VM eol.uchile.cl responde 146.83.63.70:

```text
;; ANSWER SECTION:
eol.uchile.cl.          3600    IN      CNAME   oeol-c.uchile.cl.
oeol-c.uchile.cl.       3600    IN      A       146.83.63.74
oeol-c.uchile.cl.       3600    IN      A       146.83.63.64
oeol-c.uchile.cl.       3600    IN      A       146.83.63.72
oeol-c.uchile.cl.       3600    IN      A       146.83.63.31
oeol-c.uchile.cl.       3600    IN      A       146.83.63.69
oeol-c.uchile.cl.       3600    IN      A       146.83.63.68
oeol-c.uchile.cl.       3600    IN      A       146.83.63.71
oeol-c.uchile.cl.       3600    IN      A       146.83.63.73
```

- 2 Si al iniciar su resolver hace una consulta a eol.uchile.cl, la segunda consulta a eol.uchile.cl con dig -p8000 @IP_VM da la misma dirección IP, pero respondió el caché (lo puede ver en modo debug):

```text
;; ANSWER SECTION:
eol.uchile.cl.          3600    IN      CNAME   oeol-c.uchile.cl.
oeol-c.uchile.cl.       3600    IN      A       146.83.63.74
oeol-c.uchile.cl.       3600    IN      A       146.83.63.64
oeol-c.uchile.cl.       3600    IN      A       146.83.63.72
oeol-c.uchile.cl.       3600    IN      A       146.83.63.31
oeol-c.uchile.cl.       3600    IN      A       146.83.63.69
oeol-c.uchile.cl.       3600    IN      A       146.83.63.68
oeol-c.uchile.cl.       3600    IN      A       146.83.63.71
oeol-c.uchile.cl.       3600    IN      A       146.83.63.73

;; Query time: 0 msec
```

- 3 El comando dig -p8000 @IP_VM www.uchile.cl resuelve a 200.89.76.36:

```text
;; ANSWER SECTION:
www.uchile.cl.          300     IN      A       200.89.76.36
```

- 4 El comando dig -p8000 @IP_VM cc4303.bachmann.cl resuelve a 104.248.65.245:

```text
;; ANSWER SECTION:
cc4303.bachmann.cl.     3600    IN      A       104.248.65.245
```

## Experimentos:
- 1 Preguntar por www.webofscience.com:
NO funciona, lo que sucede segun debug es esto:

```text
(debug) Consultando 'www.webofscience.com.' a '.' con dirección IP '192.33.4.12'
(debug) Consultando 'www.webofscience.com.' a 'e.gtld-servers.net.' con dirección IP '192.55.83.30'
(debug) Consultando 'www.webofscience.com.' a 'ns-342.awsdns-42.com.' con dirección IP '205.251.193.86'
(debug) Consultando 'ns-1010.awsdns-62.net.' a '.' con dirección IP '192.33.4.12'
(debug) Consultando 'ns-1010.awsdns-62.net.' a 'a.gtld-servers.net.' con dirección IP '192.55.83.30'
(debug) Consultando 'ns-1010.awsdns-62.net.' a 'g-ns-192.awsdns-62.net.' con dirección IP '205.251.192.192'
(debug) Consultando 'www.webofscience.com.' a 'ns-1010.awsdns-62.net.' con dirección IP '205.251.195.242'
```

Y no resuelve. Seguramente esto pase pq la respuesta que nos da de tipo A no sirve y las de additional tampoco y la respuesta se encuentra en CNAME (que el codigo nunca rescata). Cuando uno busca en google de hecho nos redirige a access.clarivate.com.
Se podria arreglar rescatando el CNAME y usando ese alias.
- 2 Ejecute el comando dig -p8000 @IP_VM www.cc4303.bachmann.cl ¿Qué ocurre? ¿Qué habría esperado que ocurriera? Anote sus observaciones en su informe. Contraste sus observaciones con la respuesta de ejecutar dig @8.8.8.8 www.cc4303.bachmann.cl y utilice sus conocimientos sobre DNS para explicar por qué ocurre esto.
No resuelve y como cc4303.bachman.cl si funcionaba hubiese esperado que este tambien. Cuando vemos el de google aparecen ciertas cosas: Una es status: NXDOMAIN, diciendo que no existe el dominio y vemos en authority el SOA con el servidor bachmann.cl Confirmando la no existencia.
- 3 Realice varias consultas a un mismo dominio y a través del modo debug vea a qué Name Servers y direcciones IP le pregunta su resolver en cada consulta. ¿Son siempre los mismos Name Servers? ¿Por qué cree usted que sucede esto? Anote las respuestas a estas preguntas en su informe. 

```text
(debug) Consultando 'cc4303.bachmann.cl.' a '.' con dirección IP '192.33.4.12'
(debug) Consultando 'cc4303.bachmann.cl.' a 'a.nic.cl.' con dirección IP '185.159.198.56'
(debug) Consultando 'ns1.digitalocean.com.' a '.' con dirección IP '192.33.4.12'
(debug) Consultando 'ns1.digitalocean.com.' a 'g.gtld-servers.net.' con dirección IP '192.55.83.30'
(debug) Consultando 'ns1.digitalocean.com.' a 'kim.ns.cloudflare.com.' con dirección IP '108.162.192.126'
(debug) Consultando 'cc4303.bachmann.cl.' a 'ns1.digitalocean.com.' con dirección IP '172.64.52.210'

(debug) Consultando 'www.google.com.' a '.' con dirección IP '192.33.4.12'
(debug) Consultando 'www.google.com.' a 'f.gtld-servers.net.' con dirección IP '192.55.83.30'
(debug) Consultando 'www.google.com.' a 'ns2.google.com.' con dirección IP '216.239.34.10'
```

En estos casos, intentando no usar el cache, si son siempre los mismos y tiene sentido, partimos siempre de la misma raiz, DNS es jerarquico y la delegacion de estatica. Aunque hay casos donde los dominios grandes pueden hacer round robin para repartir la carga sobre sus servidores estos van cambiando en un tiempo x que si es muy chico romperia la logica del cache por lo que es posible que no se note en este experimento.