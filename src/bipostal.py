#!/usr/bin/python

import asyncore
import getopt
import redis
import os
import sys
import logging
import struct

from config import Config
from ppymilter import (ppymilterserver,ppymilterbase)

class ResolveAddress:
    def __init__(self, config = None):
        self.config = config
        self.db_host = self.config.get('redis.host', 'localhost')
        self.db_port = int(self.config.get('redis.port', '6379'))
        self.redis = redis.Redis(host = self.db_host,
                                 port = self.db_port)
        logging.getLogger().debug("Redis connection established")

    def resolveToken(self, token):
        try:
            # Is there a better email address tokenizer? Do we need one?
            local = token.split('@')[0]
            logging.getLogger().debug("Looking up token %s" % local)
            user_address = self.redis.get('t2u:%s' % local)
            if user_address is not None:
                logging.getLogger().debug("returning %s" % local)
                return user_address
            logging.getLogger().debug("Not found!")
            return token
        except Exception, e:
            logging.getLogger().error("Exception [%s]" % str(e))
            raise

class BiPostalMilter(ppymilterbase.PpyMilter):

    config = None;

    def __init__(self):
        self.config = getConfig()
        logging.getLogger().info("Initializing BiPostal")
        super(BiPostalMilter, self).__init__()
        self.resolver = ResolveAddress(config=config)
        self.CanChangeBody()
        self._mutations = []
        self._newbody = []

    def ChangeBody(self, content):
        try:
            return '%s%s\0' % (ppymilterbase.RESPONSE['REPLBODY'], content)
        except Exception, e:
            logging.getLogger().error("Unhandled Exception [%s]", str(e))
            return None

    def OnBody(self, cmd, body = None):
        try:
            if body:
                self._newbody.append(body)
            return self.Continue()
        except Exception, e:
            logging.getLogger().error("Failure to get body [%s]", str(e))
            return self.Discard()

    def OnEndBody(self, cmd):
        logging.getLogger().debug("Applying mutations")
        if len(self._newbody):
            newbody = "%s\n%s\n%s" %("Header Stuff",
                                     "".join(self._newbody),
                                     "Footer Stuff")
            self._mutations.append(self.ChangeBody(newbody))
        actions = self._mutations
        self._mutations = []
        return self.ReturnOnEndBodyActions(actions)

    def OnResetState(self):
        logging.getLogger().info("Resetting")
        self._mutations = []


def getLogger():
    logging.basicConfig(stream = sys.stderr, level = logging.DEBUG)
    return logging.getLogger()

def getConfig(file = 'bipostal.ini'):
    if os.path.exists(file):
        return Config(file).get_map()
    logging.getLogger().warn("Config file %s not found." % file)
    return {}


if __name__ == '__main__':
    appName = sys.argv[0].split('.')[0]
    logger = getLogger()
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:d', ['config='])
        config = None
        for opt, val in opts:
            if opt in '--config':
                config = getConfig(val)
        if config is None:
            iniFileName = '%s.ini' % appName
            config = getConfig(iniFileName)
        if config is None:
            logger.error("No configuration found. Aborting")
            exit()
    except Exception, e:
        logger.error("Unhandled exception encountered. %s" % str(e))
        exit()
    port = config.get('default.port', 9999)
    logger.info("Starting bipostal on port: %s" % port)
#    bipostal = BiPostalMilter(config=config, logger=logger)
    ppymilterserver.AsyncPpyMilterServer(port, BiPostalMilter)
    asyncore.loop()