#!/usr/bin/python
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
# The Original Code is BiPostal
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

#  This file alters the content of the mail message.
# Stripping non-HTML content, wrapping with a header/footer

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


def getConfig(file = 'bipostal_milter.ini'):
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
