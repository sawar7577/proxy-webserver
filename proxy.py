import copy
import threading
import socket
import os
import sys

PROXY_PORT = 20100
CACHE_DIR = "./cache"

class Server:
    """ sever class """

    def __init__(self, config):
        self.config = config
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSocket.bind((config['HOST_NAME'], config['PORT']))
        self.serverSocket.listen(config['MAX_UCONN'])
        self.__clients = {}
        self.__client_no = 1

    def getClientName(self, cli_addr):
        """ Return the clientName with appropriate number.
        If already an old client then get the no from map, else
        assign a new number.
        """
        lock = threading.Lock()
        lock.acquire()
        ClientAddr = cli_addr[0]
        if ClientAddr in self.__clients:
            lock.release()
            return "Client-" + str(self.__clients[ClientAddr])

        self.__clients[ClientAddr] = self.__client_no
        self.__client_no += 1
        lock.release()

        return "Client-" + str(self.__clients[ClientAddr])

    def listenClient(self):
        while True:
            (clientSocket, clientAddr) = self.serverSocket.accept()
            thread = threading.Thread(name = self.getClientName(clientAddr),
                target = self.proxy_thread, 
                args = (clientSocket, clientAddr))

            thread.setDaemon(True)
            thread.start()

    def getWebserver(self, request):
        """gives port and webserver"""
        request = str(request)
        # print(request)
        # urlRequest = request.split('\n')[0]

        urlRequest = (request.split('\n')[0]).split(' ')[1]
        # print(type(request))
        httpPos = urlRequest.find("://")

        tempParse = urlRequest
        if httpPos != -1:
            tempParse = urlRequest[httpPos+3:]
        
        port_no = tempParse.find(":")

        webserver_no = tempParse.find("/")

        if webserver_no == -1:
            webserver_no = len(tempParse)

        retWebserver = ""
        retPort = -1

        if port_no == -1 or webserver_no < port_no:
            retPort = 80
            retWebserver = tempParse[:webserver_no]
        else:
            retPort = int((tempParse[port_no+1: ])[:webserver_no - port_no - 1])
            retWebserver = tempParse[:port_no]

        return (retWebserver, retPort)

        
    
    def proxy_thread(self, conn, clientAddr):

        request = conn.recv(self.config['MAX_REQUEST_LEN'])
        print("thread created")

        webserver = self.getWebserver(request)
        print(webserver)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.config['CONNECTION_TIMEOUT'])
        s.connect(webserver)
        s.sendall(request)

        while 1:
            data = s.recv(self.config['MAX_REQUEST_LEN'])
            if (len(data) > 0):
                conn.send(data)
            else:
                break

        s.close()
        conn.close()


if __name__ == "__main__":
    config = {
        "MAX_REQUEST_LEN" : 1024,
        "HOST_NAME" : "0.0.0.0",
        "PORT" : 12345,
        "MAX_UCONN" : 50,
        "CONNECTION_TIMEOUT" : 5,
    }
    server = Server(config)
    server.listenClient()