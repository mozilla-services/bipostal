#!/usr/bin/python

import asyncore
import getopt
import redis
import os
import sys
import logging

from config import Config
from ppymilter import (ppymilterserver,ppymilterbase)

class ResolveAddress:
    def __init__(self, config = None, logger = None):
        self.config = config
        self.logger = logger
        self.db_host = self.config.get('redis.host', 'localhost')
        self.db_port = int(self.config.get('redis.port', '6379'))
        self.redis = redis.Redis(host = self.db_host,
                                 port = self.db_port)
        logger.debug("Redis connection established")

    def resolveToken(self, token):
        try:
            # Is there a better email address tokenizer? Do we need one?
            local = token.split('@')[0]
            logger.debug("Looking up token %s" % local)
            user_address = self.redis.get('t2u:%s' % local)
            if user_address is not None:
                logger.debug("returning %s" % local)
                return user_address
            logger.debug("Not found!")
            return token
        except Exception, e:
            self.logger("Exception [%s]" % str(e))
            raise

class BiPostalMilter(ppymilterbase.PpyMilter):

    config = None;
    logger = None;

    def __init__(self):
        self.logger = getLogger()
        self.config = getConfig()
        logger.info("Initializing BiPostal")
        super(BiPostalMilter, self).__init__()
        self.resolver = ResolveAddress(config=config,
                                  logger=logger)
        self.CanAddHeaders()
        self.CanChangeHeaders()
        self._mutations = []

    def OnRecptTo(self, cmd, rcpt_to, esmtp_info):
        try:
            self.logger.debug("OnRecpTo: %s" % rcpt_to)
            address = resolver.resolveToken(rcpt_to)
            self._mutations.append(self.ChangeHeader(0, 'To', address))
        except Exception, e:
            self.logger.error("Discarding message: [%s]", str(e))
            self.Discard()

    def OnEndBody(self, cmd):
        actions = self._mutations
        self.logger.debug("Applying mutations")
        self._mutations = []
        return self.ReturnOnEndBodyActions(actions)

    def OnResetState(self):
        self.logger.info("Resetting")
        self._mutations = []

    def OnMacro(self, cmd, macro_cmd, data):
        if macro_cmd == 'R':

            address = self.resolver.resolveToken(data[5])
            if address is not None:
                local, host = address.split('@',2)
                data[5] = local
                data[3] = host
                return data
        return None

def getLogger():
    logging.basicConfig(stream = sys.stderr, level = logging.INFO)
    return logging.getLogger()

def getConfig(logger = None):
    if logger is None:
        logger = getLogger()
    return Config('bipostal.ini').get_map()


if __name__ == '__main__':
    appName = sys.argv[0].split('.')[0]
    logger = getLogger()
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
            logger.error("No configuration found. Aborting")
            exit()
    except Exception, e:
        logger.error("Unhandled exception encountered. %s" % str(e))
        exit()
    port = config.get('default.port', 9999)
    import pdb; pdb.set_trace();
    logger.info("Starting bipostal on port: %s" % port)
#    bipostal = BiPostalMilter(config=config, logger=logger)
    ppymilterserver.AsyncPpyMilterServer(port, BiPostalMilter)
    asyncore.loop()