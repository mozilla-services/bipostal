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

import getopt
import logging
import os
import re
import sys
import time

from bipostal.storage import configure_from_settings
from config import Config
from mako.template import Template
from ppymilter2 import (ppymilterserver, ppymilterbase)


class BiPostalMilter(ppymilterbase.PpyMilter):
    """ Modify the mailer body and add header/footer content

        TODO:
        * strip HTML content in favor of plain text.
        * add Templater for header/footer code
        * fetch user personalization content (needed?)
        * use standardized config loader
    """

    config = None
    _dtime = 0

    def __init__(self, config=None):
        if config is None:
            self.config = getConfig()
        else:
            self.config = config
        logging.getLogger().info("Initializing BiPostal")
        super(BiPostalMilter, self).__init__()
        # Ask for permissions
        self.CanChangeBody()
        self.CanChangeHeaders()
        self.CanAddHeaders()
        #init variables
        self._hasCT = False
        self._mutations = []
        self._boundary = None
        self._newbody = []
        self._toCount = 1
        self._info = {}
        self._split = None
        template_dir = os.path.join(self.config.get('default.template_dir',
                                                    'templates'))
        self.txt_head_template = Template(filename = os.path.join(template_dir, 
                'head_txt.mako'))
        self.txt_foot_template = Template(filename = os.path.join(template_dir, 
                'foot_txt.mako'))
        self.html_head_template = Template(filename = os.path.join(template_dir, 
                'head_html.mako'))
        self.html_foot_template = Template(filename = os.path.join(template_dir, 
                'foot_html.mako'))
        self.storage = configure_from_settings('storage', self.config)

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

    def OnHeader(self, cmd, header, val=None):
        stime = time.time()
        lhead = header.lower()
        if 'content-type' in lhead:
            self._hasCT = True
            if 'multipart' in val.lower():
                matches = re.search('boundary="([^"]*)"', val)
                if matches and len(matches.groups()):
                    self._boundary= matches.group(1)
        self._dtime += time.time() - stime
        return self.Continue()

    def OnBody(self, cmd, body = None):
        try:
            if body:
                stime = time.time()
                if self._boundary is not None:
                    for element in body.split(self._boundary):
                        try:
                            (subHead, subBody) = element.split("\r\n\r\n", 1)
                            if 'text/plain' in subHead:
                                self._newbody.append(subBody)
                        except ValueError:
                            pass
                else:
                    self._newbody.append(body)
                self._dtime += time.time() - stime
                if len(self._newbody):
                    return self.Continue()
            logging.getLogger().error("No plain body found")
            return self.Reject()
        except Exception, e:
            logging.getLogger().error("Failure to get body [%s]" % repr(e))
            return self.Discard()

    def OnRcptTo(self, cmd, rcpt_to, esmtp_info):
        stime = time.time()
        try:
            # if an address record is set as inactive, we shouldn't send the notification,
            # but should we still send the mail? That is currently undecided.
            self._info = self.storage.resolve_alias(rcpt_to)
            if self._info is not None:
                status = self._info.get('status', 'invalid')
                if status == 'active':
                    self._mutations.append(self.ChangeHeader(self._toCount, 
                        'To', self._info['email']))
                    self._toCount = self._toCount + 1
                    self._dtime += time.time() - stime
                    return self.Continue();
                if status == 'inactive':
                    self._dtime += time.time() - stime
                    logging.getLogger().debug('%s is inactive, Discarding' %
                            self._info.get('alias')) 
                    return self.Discard()
        #default case: status is "deleted" or "invalid", or an error 
        # so reject the message
        except Exception, e:
            logging.getLogger().error("Address lookup failure [%s]" % repr(e))
            pass
        self._dtime += time.time() - stime
        return self.Reject()

    def getSplit(self):
        if self._boundary is None:
            self._boundary = "---split-%s" % str(int(time.time()))
        return self._boundary

    def OnEndBody(self, cmd):
        stime = time.time()
        logging.getLogger().debug("Applying mutations")
        self._info['manageurl'] = self.config.get('manageurl', 
                'https://bipostal.diresworb.org/#default')
        if len(self._newbody):
            splitter = ('multipart/alternative; boundary="%s"'
                    ) % self.getSplit()
            if self._hasCT:
                self._mutations.append(
                    self.ChangeHeader(1, 'Content-Type', splitter))
            else:
                self._mutations.append(
                    self.AddHeader(999, 'Content-Type', splitter))
            newtxtbody = "%s\r\n%s\r\n%s" % (
                self.txt_head_template.render(info = self._info),
                "".join(self._newbody),
                self.txt_foot_template.render(info = self._info))
            newhtmlbody = "%s\r\n%s\r\n%s" % (
                self.html_head_template.render(info=self._info),
                "".join(self._newbody),
                self.html_foot_template.render(info=self._info))
            newmsg = ("--%s\r\n"
                "Content-Type: text/plain; charset=utf-8;\r\n"
                "Content-Transfer-Encoding: 7bit\r\n\r\n"
                "%s\r\n"
                "--%s\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                "Content-Transfer-Encoding: 7bit\r\n\r\n"
                "%s\r\n"
                "--%s\r\n") % (
                    self.getSplit(),
                    newtxtbody,
                    self.getSplit(),
                    newhtmlbody,
                    self.getSplit())
            self._mutations.append(self.ChangeBody(newmsg))
        actions = self._mutations
        self._mutations = []
        self._dtime += time.time() - stime
        logging.getLogger().info("total time: %d" % self._dtime)
        return self.ReturnOnEndBodyActions(actions)

    def OnResetState(self):
        logging.getLogger().info("Resetting")
        self._mutations = []
        self._dtime=0;


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
    server = ppymilterserver.PPYMilterServer(listener=('0', port),
            handler=BiPostalMilter).server
    server.serve_forever()

