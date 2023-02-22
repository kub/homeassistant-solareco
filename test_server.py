#!/usr/bin/env python3

import socket
import time
import string

# Read "distributed echo server" as "(distributed echo) server". The "server"
# is not "distributed" but the echos are "distributed" to every connected
# client.

# Connect to the server with `telnet localhost 5000`.

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(False)
server.bind(('localhost', 5000))
server.listen(5)

connections = []

while True:
    try:
        connection, address = server.accept()
        connection.setblocking(False)
        connections.append(connection)
    except BlockingIOError:
        pass
    for connection in connections:
        try:
            letters = string.ascii_lowercase
            connection.send(b'M:4 P:1:1 R:0 F:0 U:168 168V 838mA 140W 50Hz 30C 594us 252Wh\n')
            time.sleep(2)
        except Exception:
            connections.remove(connection)
