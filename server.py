import socket
import sys

soc = socket.socket()

if len(sys.argv) != 2:
    print "enter port no for server"
    exit(0)

port = int(sys.argv[1])
print port
soc.bind(('',port))

soc.listen(5)

while True:
    conn, addr = soc.accept()
    print "connection request from " + str(addr)
    data = conn.recv(1024).decode()
    if not data:
        conn.close()
        continue
    print "Data recieved: "  + str(data)  
    conn.send('Thank You')
    conn.close()