import socket
import sys
import base64

soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# soc = socket.socket()
# host = gethostname()
if len(sys.argv) < 2:
    print "enter port no for client"
    exit(0)
creds = str(sys.argv[2]) + ':' + str(sys.argv[3])

port = int(sys.argv[1])
soc.connect(('127.0.0.1',20100))
request = 'GET localhost:' + sys.argv[1] + ' HTTP/1.1\n'
request += 'Host: localhost:' + sys.argv[1]
request += '\nAuthorization: Basic ' + base64.b64encode(creds)
request += '\nAccept-Encoding: gzip, deflate\n'
request += 'Connection: keep-alive\n\n'
soc.send(request)
data = soc.recv(1024)
print "server response: " + str(data)
soc.close()