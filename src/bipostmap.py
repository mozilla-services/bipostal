import asynchat
import asyncore
import getopt
import logging
import os
import redis
import socket
import sys

from config import Config


class ResolveAddress(object):
    """ Connect to redis database to resolve the local-part to the outbound
        email address

        TODO:
        * add abstract data class to connect to same db as Push
        * add comments and clean up
    """
    def __init__(self, config = None):
        self.config = config
        self.db_host = self.config.get('redis.host', 'localhost')
        self.db_port = int(self.config.get('redis.port', '6379'))
        try:
            self.redis = redis.Redis(host = self.db_host,
                                 port = self.db_port)
            logging.getLogger().debug("Redis connection established")
        except Exception, e:
            logging.getLogger().error("Redis connection failed %s",  str(e))
            raise BiPostmapException("DB Failure")

    def resolveToken(self, token):
        try:
            local = token.split('@')[0]
            user_address = self.redis.get('s2u:%s' % local)
            if user_address is not None:
                logging.getLogger().debug('returning %s' % local)
                return user_address
            logging.getLogger().debug("Not found!")
            return None
        except Exception, e:
            logging.getLogger().error("Unhandled Exception [%s]" % str(e))
            raise


class BiPostmapException(Exception):
    """ Browser ID Postmap Exception """
    def __init__(self, code, message):
        self.code = code
        self.msg = message

    def __str__(self):
        return "[%s] %s" % (self.code, self.msg)


class BiPostmapServer(asyncore.dispatcher):

    def __init__(self, port, server_class, config=None):
        asyncore.dispatcher.__init__(self)
        self._server_class = server_class
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('', config.get('default.port', 9998)))
        self.listen(config.get('default.max_queued_connections', 1024))
        self.config = config

    def handle_accept(self):
        """Callback function from asyncore to handle a connection
        dispatching."""
        try:
            (conn, addr) = self.accept()
        except socket.error, e:
            logging.getLogger().warn('warning: server accept() ' +
                    'threw an exception ("%s")', str(e))
            return None
        BiPostmapConnectionHandler(conn,
                                    addr,
                                    self._server_class,
                                    config)


class BiPostmapDispatcher(object):

    def __init__(self, server_class, config = None):
        self._server_class = server_class(config)

    def dispatch(self, data):
        try:
            # Commands are either GET or PUT, Only GET is recognized.
            cmd, data = data.strip().split(' ')
            if "GET" not in cmd.upper():
                return {'name': 'Unsupported command', 'code': 400}
            username = self._server_class.resolveToken(data)
            if username:
                return {'name': username, 'code': 200}
            return {'name': 'Unrecognized Address', 'code': 500}
        except Exception, e:
            logging.getLogger().info('Perm Failure: %s', str(e))
            return {'name': 'Lookup failure', 'code': 400}


class BiPostmapConnectionHandler(asynchat.async_chat):

    def __init__(self, conn, addr, server_class, config=None):
        asynchat.async_chat.__init__(self, conn)
        self._conn = conn
        self._addr = addr
        self._dispatcher = BiPostmapDispatcher(server_class, config)
        self._input = []
        self.set_terminator("\n")
        self.found_terminator = self.read_data

    def collect_incoming_data(self, data):
        """Callback from asynchat--simply buffer partial data in a string."""
        self._input.append(data)

    def log_info(self, message, type='info'):
        """Provide useful logging for uncaught exceptions"""
        if type == 'info':
            logging.getLogger().debug(message)
        else:
            logging.getLogger().error(message)

    def respond(self, response):
        if 'name' not in response:
            raise BiPostmapException("missing return name")
        logging.getLogger().debug('  >>> [%s] %s' % (response.get('code', 400),
                                         response.get('name')))
        self.push("%d %s\n" % (int(response.get('code', 400)),
                                str(response.get('name'))))

    def read_data(self):
        inbuff = "".join(self._input)
        self._input = []
        logging.getLogger().debug(' request: %s' % inbuff)
        try:
            response = self._dispatcher.dispatch(inbuff)
            if type(response) == list:
                for r in response:
                    self.respond(r)
            elif response:
                self.respond(response)
            else:
                self.respond({'name': 'Unknown Recipent', 'code': 500})
        except Exception, e:
            logging.getLogger().error("Unexpected error %s " % str(e))
            self.respond({'name': 'Unexpected error', 'code': 400})
        self.close()


if __name__ == '__main__':
    appName = sys.argv[0].split('.')[0]
    logging.basicConfig(stream = sys.stderr, level = logging.DEBUG)
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:d', ['config='])
        config = None
        for opt, val in opts:
            if opt in '--config':
                config = Config(val).get_map()
        if config is None:
            iniFileName = '%s.ini' % appName
            if os.path.exists(iniFileName):
                config = Config(iniFileName).get_map()
        if config is None:
            logging.getLogger().error("No configuration found. Aborting")
            exit()
    except Exception, e:
        logging.getLogger().error("Unhandled exception encountered. %s" %
                str(e))
        exit()
    port = config.get('default.port', 9998)
    logging.getLogger().info("Starting bipostmap on port: %s" % port)
    # Sets the BiPostmapServer as the async core server.
    server = BiPostmapServer(port, ResolveAddress, config = config)
    asyncore.loop()
