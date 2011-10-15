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

    def resolveToken(self, token):
        try:
            # Is there a better email address tokenizer? Do we need one?
            local = token.split('@')[0]
            user_address = self.redis.get('t2u:%s' % local)
            if user_address is not None:
                return user_address
        except Exception, e:
            self.logger("Exception [%s]" % str(e))
            raise

class BiPostalMilter(ppymilterbase.PpyMilter):

    config = None;
    logger = None;

    def __init__(self, config = None, logger = None):
        self.config = config
        self.logger = logger
        super(BiPostalMilter, self).__init__()
        resolver = ResolveAddress(config=config,
                                  logger=logger)
        self.CanAddHeaders()
        self.CanChangeHeaders()
        self._mutations = []

    def OnRecptTo(self, cmd, rcpt_to, esmtp_info):
        try:
            address = resolver.resolveToken(rcpt_to)
            self._mutations.append(self.ChangeHeader(0, 'To', address))
        except Exception, e:
            logger.error("Discarding message: [%s]", str(e))
            self.Discard()

    def OnEndBody(self, cmd):
        actions = self._mutations
        self._mutations = []
        return self.ReturnOnEndBodyActions(actions)

    def OnResetState(self):
        self._mutations = []

if __name__ == '__main__':
    appName = sys.argv[0].split('.')[0]
    import pdb; pdb.set_trace();
    logging.basicConfig(stream = sys.stderr, level = logging.INFO)
    logger = logging.getLogger()
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
    bipostal = BiPostalMilter(config=config, logger=logger)
    ppymilterserver.AsyncPpyMilterServer(config.get('default.port', 9999),
                                         bipostal)
    asyncore.loop()