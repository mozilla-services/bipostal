# -*- coding: iso-8859-15 -*-
"""Simple FunkLoad test

$Id$
"""
import unittest
import random
import time
from config import Config
from bipostal.storage import configure_from_settings
from funkload.FunkLoadTestCase import FunkLoadTestCase
from fake_webunit import (fetch, Sock)
from sqlalchemy.exc import ProgrammingError

class DummyResponse(object):
    headers = []
    code = 200

    def __init__(self, value):
        self.url = value


class Simple(FunkLoadTestCase):
    """This test use a configuration file Simple.conf."""

    dbLoaded = False
    
    """    
    def __init__(self, *arg, **kw):
        print "Init..."
        import pdb; pdb.set_trace()
        super(FunkLoadTestCase, self).__init__(*arg, **kw)
    """
    def setUp(self):
        """Setting up test."""
        self.max_load = self.conf_getInt('main', 'max_load', 10000)
        self.load_size = len(str(self.max_load))
        self._browser.fetch = fetch
        self.alias_t = 'alias_%%0%dd@example.com' % self.load_size
        self.user_t = 'user_%%0%dd@example.com' % self.load_size 
        if (self.isTrue(self.conf_get('main', 'load_db', 'False')) 
                and self.dbLoaded == False):
            print 'Loading DB...'
            try:
                for i in range(0, self.max_load):
                    if (i % 10000) == 0:
                        print i;
                    storage.add_alias(user=self.user_t % i, 
                        alias=self.alias_t % i, 
                        origin='example.com')
                print 'DB Loaded'
            except ProgrammingError, e:
                print repr(e)
                pass
        self.dbLoaded = True

    def test_aaload(self):
        # ignore this test, used to prime the db.
        pass

    def isTrue(self, string):
        if string.lower() == 'true':
            return True
        if string.lower() == 'yes': 
            return True
        return False;

    def txxest_mapper(self):
        # The description should be set in the configuration file
        # begin of test ---------------------------------------------
        nb_time = self.conf_getInt('test_mapper', 'nb_time')
        for i in range(nb_time):
            rand = random.randint(0, self.max_load)
            server_url = 'http://%s:%s/%s' % (
                    self.conf_get('test_mapper', 'host'),
                    self.conf_get('test_mapper', 'port'),
                    self.alias_t % rand)
            resp = self.get(server_url, description='Get url')
            self.failUnless(resp.body == (self.user_t % rand))
        # end of test -----------------------------------------------

    def test_milter(self):
        # Under work. Need to get the protocol down wfor this.
        nb_time  = self.conf_getInt('test_milter', 'nb_time')
        for i in range(nb_time):
            rand = random.randint(0, self.max_load)
            self.steps += 1
            self.page_responses = 0
            alias = self.alias_t % rand;
            self.logd('GET %s\n\tPage %i' % (alias, self.steps))
            t_start = time.time()
            sock = Sock(self.conf_get('test_milter', 'host'),
                   self.conf_get('test_milter', 'port'))
            #option negotiation
            #Do everything
            #resp = sock.mexchange ("O\00\00\00\06\00\00\01\xFF\00\x1F\xFF\xFF", single=True)
            resp = sock.mexchange ('R<%s>\000RCPT\x3Drfc822;%s\00' % (
                alias,
                alias))
            #resp should be 'c'
            resp = sock.mexchange ('Btesting 123\n\n')
            resp = sock.mexchange ('E\00\00\00')
            t_stop = time.time()
            #self.failUnless(resp[0][:1] == 'm' and (self.user_t % rand) in resp[0])
            #self.failUnless(resp[1][:1] == 'b' and 'testing 123' in resp[1])
            t_delta = t_stop - t_start
            self.total_time += t_delta
            self.total_pages += 1
            self.logd(' Done in %.3fs' % t_delta)
            self._log_response(DummyResponse(alias), 'sock', alias, t_start, t_stop) 

if __name__ in ('main', '__main__'):
    bi_config = Config('../src/bipostmap.ini').get_map()
    #filter the config.
    config = {}
    for key in filter(lambda x: x.startswith('storage'), bi_config):
        config[key[8:]] = bi_config[key]
    storage = configure_from_settings('storage', config)
    unittest.main()
    storage.flushall(pattern='alias_%')
