import urlparse
from StringIO import StringIO
import socket
import struct
from webunit.webunittest import HTTPResponse

def fetch(url, 
        postdata=None, 
        server=None, 
        port=None, 
        protocol=None, 
        ok_codes=None,
        **kw):
    """ Replace the fetch with something a bit more direct """
    t_protocol, t_server, t_url, x, t_args, x = urlparse.urlparse(url)
    t_port = None
    url = t_url[1:]
    if server is None:
        if ':' in t_server:
            t_server, t_port = t_server.split(':')
        server = t_server
        if port is None and t_port is not None:
            port = t_port
    if protocol is None:
        protocol = t_protocol

    #do socket call here.

    sock = Sock(server, port)
    response = sock.exchange("GET %s\n" %url)
    sock.close()
    error_content = []
    code, user = response.strip().split(' ', 1)
    response = HTTPResponse([], protocol, server, port, url, 
                int(code), user, {}, user, error_content)

    return response


class Sock(object):
    _sock = None

    def __init__(self, server, port):
        self._sock = self.connect(server, port)

    def connect(self, server, port):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.connect((server, int(port)))
        return self._sock

    def msend(self, string):
        self._sock.send("%s%s" % (struct.pack('!I', len(string)), 
                                    string))

    def mrecv(self):
        plen = self._sock.recv(4)
        data = self._sock.recv(struct.unpack('!I', plen)[0])
        return data

    def mexchange(self, string, single=False):
        resp = []
        if (type(string) == type([])):
            for str in string:
                self.msend(string)
        else:
            self.msend(string)
        while 1:
            data = self.mrecv()
            resp.append(data);
            if data == 'c' or single == True:
                break
        return resp;

    def exchange(self, string):
        self._sock.send(string)
        string = StringIO()
        while 1:
            data = self._sock.recv(1024)
            if len(data) < 1:
                break;
            string.write(data)
        return string.getvalue()

    def close(self):
        if self._sock != None:
            self._sock.close()
            self._sock = None;

