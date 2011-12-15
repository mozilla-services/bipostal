# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is BIPostal-bipostmap
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   JR Conlin (jrconlin@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

# This file remaps token@host.tld to the registered email. 
# This app uses the common bipostal_store libraries for data mgmt.
from bipostal.storage import configure_from_settings
from config import Config
import asynchat
import asyncore
import getopt
import logging
import os
import socket
import sys

class ResolveAddress(object):
    """ Connect to redis database to resolve the local-part to the outbound
        email address

        TODO:
        * add abstract data class to connect to same db as Push
        * add comments and clean up
    """
    def __init__(self, config = None):
        self.config = config
        self.storage = configure_from_settings('storage', 
                self.config)

    def resolve_alias(self, token):
        try:
            user_address = self.storage.resolve_alias(token)
            if user_address is not None:
                logging.getLogger().debug('returning %s' % user_address)
                return user_address.get('email')
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

    def __init__(self, port, resolver, config=None):
        if config  is None:
            self.config = _get_conf();
        else:
            self.config = config
        if port is None:
            port = config.get('default.port', 9998)
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('', port))
        self.resolver = resolver
        self.listen(config.get('default.max_queued_connections', 1024))

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
                                    self.resolver,
                                    config)


class BiPostmapDispatcher(object):

    def __init__(self, resolver, config = None):
        self.resolver = resolver(_get_group(config, 'storage'))

    def dispatch(self, data):
        try:
            # Commands are either GET or PUT, Only GET is recognized.
            cmd, data = data.strip().split(' ')
            if "GET" not in cmd.upper():
                return {'name': 'Unsupported command', 'code': 400}
            username = self.resolver.resolve_alias(data)
            if username:
                return {'name': username, 'code': 200}
            return {'name': 'Unrecognized Address', 'code': 500}
        except Exception, e:
            logging.getLogger().error('Perm Failure: %s', str(e))
            return {'name': 'Lookup failure', 'code': 400}


class BiPostmapConnectionHandler(asynchat.async_chat):

    def __init__(self, conn, addr, resolver, config=None):
        asynchat.async_chat.__init__(self, conn)
        self._conn = conn
        self._addr = addr
        self._dispatcher = BiPostmapDispatcher(resolver, 
                config)
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


def _get_conf():
    appName = sys.argv[0].split('.')[0]
    iniFileName = '%s.ini' % appName
    if os.path.exists(iniFileName):
        config = Config(iniFileName)
        return config
    return None

def _get_group(dictionary, group):
    if group is None:
        return dictionary
    else:
        ret = {}
        for key in filter(lambda x: x.startswith(group), dictionary):
            ret[key[len(group)+1:]] = dictionary[key]
        return ret

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
            config = _get_conf().get_map()
        if config is None:
            logging.getLogger().error("No configuration found. Aborting")
            exit()
    except Exception, e:
        logging.getLogger().error("Unhandled exception encountered. %s" %
                str(e))
        exit()
    port = int(config.get('default.port', '9998'))
    logging.getLogger().info("Starting bipostmap on port: %s" % port)
    # Sets the BiPostmapServer as the async core server.
    server = BiPostmapServer(port, ResolveAddress, config = config)
    asyncore.loop()
