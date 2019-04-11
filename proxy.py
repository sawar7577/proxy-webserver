import copy
import threading
import socket
import os
import sys
import base64
import datetime

PROXY_PORT = 20100
CACHE_DIR = "./cache"
SITE_COUNT = {}
CACHE_DICT = {}
class Server:
    """ sever class """

    def __init__(self, config):
        self.config = config
        self.serverSocket = socket.socket()
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSocket.bind(('', config['PORT']))
        self.serverSocket.listen(config['MAX_UCONN'])
        self.__clients = {}
        self.__client_no = 1
        self.request = ""

    def incCount(self,url):
        if url in SITE_COUNT:
            now = datetime.datetime.now()
            # print(type(now), type(SITE_COUNT[url][1]))
            tdelta = now - SITE_COUNT[url][1]
            if tdelta.seconds < 300:
                print(tdelta.seconds)
                SITE_COUNT[url] = (1+SITE_COUNT[url][0], SITE_COUNT[url][1])
            else:
                SITE_COUNT[url] = (1, datetime.datetime.now())
        else:
            SITE_COUNT[url] = (1, datetime.datetime.now())

        print(SITE_COUNT[url])
    
    def addToCache(self, webserver,s,conn,request):
        st = b''
        print("file made")
        s.send(request)

        try:
            while True:
                data = s.recv(self.config['MAX_REQUEST_LEN'])
                if (len(data) > 0):
                    st = st + data
                else:
                    break
            # CACHE_DICT[webserver] = (st, time.time())
        except:
            pass
        CACHE_DICT[webserver] = (st, datetime.datetime.utcnow())
        print("complete")

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

    def check_blocked(self,webserver):
        f = open('proxy/blacklist.txt', "rb")
        data = ""   
        while True:
            chunk = f.read()
            if not len(chunk):
                break
            data += chunk
        f.close()
        blocked = data.split('\n')    
        ip = str(socket.gethostbyname(webserver[0]))    
        ip += ':' + str(webserver[1])
        if ip in blocked:
            return True
        
        return False    

    def get_creds(self):
        f = open('credentials.txt', "rb")
        data = ""   
        while True:
            chunk = f.read()
            if not len(chunk):
                break
            data += chunk
        f.close()
        
        blocked = data.split('\n')
        cred_list = []
        for cred in blocked:
            cred_list.append(base64.b64encode(cred))
        return cred_list   

    def get_auth(self,request):
        
        blocked = request.splitlines() 
        auth_line = [ line for line in blocked if "Authorization" in line]
        
        if len(auth_line):
            auth = auth_line[0].split()[2]
        else:
            auth = None
        return auth
    
    def get_request(self,request):
        
        blocked = request.splitlines() 
        for line in blocked:
            if "POST" in line:
                return "post"
            else:
                return "get"

    def proxy_thread(self, conn, clientAddr):

        # print int(clientAddr[1])
        # if int(clientAddr[1]) < 20000 or int(clientAddr[1]) > 20099:
        #     data = "Client address out side of IIIT\n"
        #     conn.send(data)
        #     conn.close()
        #     return

        request = conn.recv(self.config['MAX_REQUEST_LEN'])
        req = copy.deepcopy(request)
        print("thread created")
        # print req
        req_type = self.get_request(request)
        print req_type
        webserver = self.getWebserver(request)
        urlRequest = (str(request).split('\n')[0]).split(' ')[1]
        print(webserver)
        if self.check_blocked(webserver):
            data = "Blacklisted site:Authorization Failed\n"
            cred_list = self.get_creds()
            print cred_list
            auth = self.get_auth(request)
            if auth in cred_list:
                print "Authorization Successful"
            else:   
                conn.send(data)
                conn.close()
                return
        # print request

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.config['CONNECTION_TIMEOUT'])
        
        try:
            s.connect(webserver)
            s.sendall(req)
        except:
            data = "Connection Failed\n"
            conn.send(data)
            conn.close()
            return
        
        
        if req_type == "get":       
           
            use_cache = False
            self.incCount(urlRequest) 
            if SITE_COUNT[urlRequest][0] == 3:
                self.addToCache(urlRequest,s,conn,request)
                use_cache = True
            elif SITE_COUNT[urlRequest][0] > 3:
                use_cache = True

            if use_cache and urlRequest in CACHE_DICT:
                header = "If-Modified-Since: " + str(CACHE_DICT[urlRequest][1].strftime('%a, %d %b %Y %H:%M:%S')) + " GMT"
                requestTemp = request.decode()
                tokens = requestTemp.split('\r\n')
                tokens.insert(-2, header)
                tokens = '\r\n'.join(tokens)
                tokens = tokens.encode()
                s.send(tokens)
                reply = b''
                while True:
                    data = s.recv(self.config['MAX_REQUEST_LEN'])
                    if len(reply) > 0:
                        reply += data
                    else:
                        break
                reply = reply.decode()
                if '304' in reply:
                    print "Page Modified"
                    s.send(req)
                    while 1:
                        data = s.recv(self.config['MAX_REQUEST_LEN'])
                        if (len(data) > 0):
                            conn.send(data)
                        else:
                            break
                else:
                    print "\nUsing Cache\n"
                    try:
                        conn.settimeout(10)
                        conn.sendall(CACHE_DICT[urlRequest][0])
                    except Exception as e:
                        print(e)
            else:
                while 1:
                    data = s.recv(self.config['MAX_REQUEST_LEN'])
                    if (len(data) > 0):
                        conn.send(data)
                    else:
                        break
        else:
            print "post request " + request.splitlines()[-1]
            while 1:
                reply = s.recv(1024)
                if len(reply):
                    conn.send(reply + "\nYour Data: " + request.splitlines()[-1] + "\n")
                else:
                    break

        s.close()
        conn.close()


if __name__ == "__main__":
    config = {
        "MAX_REQUEST_LEN" : 1024,
        "HOST_NAME" : "127.0.0.1",
        "PORT" : 20100,
        "MAX_UCONN" : 50,
        "CONNECTION_TIMEOUT" : 35,
    }
    server = Server(config)
    server.listenClient()