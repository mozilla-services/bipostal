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
from gevent.server import StreamServer
from gevent.pool import Pool
import getopt
import logging
import os
import sys

class ResolveServer(StreamServer):

    def __init__(self, listener, config, **kw):
        super(ResolveServer, self).__init__(listener, **kw)
        self.config = config
        self.storage = configure_from_settings('storage',
                self.config)

    def handle(self, socket, address):
        try:
            sock = socket.makefile()
            inline = sock.readline()
            cmd, alias = inline.split(' ',2)
            if cmd.upper() != 'GET':
                sock.write("500 Invalid Command\n")
            else:
                import pdb;pdb.set_trace()
                user_address = self.storage.resolve_alias(alias.strip())
                if (user_address is not None and
                    user_address.get('email', None) is not None):
                    logging.getLogger().debug('returning %s' % user_address)
                    sock.write("200 %s\n" % user_address.get('email'))
                else:
                    logging.getLogger().debug("Not found!")
                    sock.write("500 Address not found\n")
        except Exception, e:
            logging.getLogger().error("Unhandled Exception [%s]" % str(e))
            sock.write("400 Server Error\n")
            raise
        finally:
            sock.flush()


def _get_conf():
    appName = sys.argv[0].split('.')[0]
    iniFileName = '%s.ini' % appName
    if os.path.exists(iniFileName):
        config = Config(iniFileName)
        return config
    logging.error('No Config file found.')
    return None


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
    max_connects = int(config.get('default.max_connections', 1))
    
    logging.getLogger().info("Starting bipostmap on port: %s" % port)
    # Sets the BiPostmapServer as the async core server.
    pool = Pool(max_connects)
    server = ResolveServer(('127.0.0.1', port), config=config, spawn=pool)
    server.serve_forever()
