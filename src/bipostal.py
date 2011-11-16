#!/usr/bin/python

import asyncore
import getopt
import logging
import os
import sys

from config import Config
from mako.template import Template
from ppymilter import (ppymilterserver, ppymilterbase)


class BiPostalMilter(ppymilterbase.PpyMilter):
    """ Modify the mailer body and add header/footer content

        TODO:
        * strip HTML content in favor of plain text.
        * add Templater for header/footer code
        * fetch user personalization content (needed?)
        * use standardized config loader
    """

    config = None

    def __init__(self):
        self.config = getConfig()
        logging.getLogger().info("Initializing BiPostal")
        super(BiPostalMilter, self).__init__()
        self.CanChangeBody()
        self._mutations = []
        self._newbody = []
        self._info = {}

    def ChangeBody(self, content):
        try:
            #NOTE: Postfix ONLY understands strings. Yes, this is overkill because 
            # there are some instances where unicode sneaks through and it causes
            # all sorts of Heisenbugs.
            return str('%s%s' % 
                    (ppymilterbase.RESPONSE['REPLBODY'], 
                    str(content)))
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
        template_dir = os.path.join(self.config.get('default.template_dir',
                                                    'templates'))
        head_template = Template(filename = os.path.join(template_dir, 
                'head.mako'))
        foot_template = Template(filename = os.path.join(template_dir, 
                'foot.mako'))

        if len(self._newbody):
            newbody = "%s\n%s\n%s" % (head_template.render(info = self._info),
                                     "".join(self._newbody),
                                     foot_template.render(info = self._info))
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
    ppymilterserver.AsyncPpyMilterServer(port, BiPostalMilter)
    asyncore.loop()
