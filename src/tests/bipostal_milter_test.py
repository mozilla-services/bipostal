import unittest
from config import Config
from bipostal.storage import configure_from_settings
from src.bipostal_milter import BiPostalMilter

class TestMilter(unittest.TestCase):

    def setUp(self):
        raw_config = Config('src/tests/test_config.ini').get_map()
        config={}
        for key in filter(lambda x: x.startswith('storage'), raw_config):
            config[key[8:]] = raw_config[key]
        self.storage = configure_from_settings('storage', config)
        self.alias_t = 'alias@example.com'
        self.user_t = 'user@example.com'
        self.storage.add_alias(
                email=self.user_t,
                alias=self.alias_t,
                origin='example.com')
        self.milter = BiPostalMilter(config=raw_config)

    def tearDown(self):
        self.storage.flushall(pattern='alias@example.com')
        pass

    def test_all(self):
        body = """
message cruft
---split
Content-Type: text/plain; charset=UTF-8; format=flowed\r
Content-Transfer-Encoding: 7bit\r
\r
Plain text content

---split
Content-Type: text/html; charset=UTF-8;\r
Content-Transfer-Encoding: 7bit\r
\r
<i>Invalid Content</i>

---split 
"""
        resp = self.milter.OnHeader('H', 'content-type', 'multipart boundry="--split"')
        resp = self.milter.OnRcptTo('R', self.alias_t, '')
        self.assertEquals(resp, 'c')
        resp = self.milter.OnBody('B', body)
        self.assertEquals(resp, 'c')
        resp = self.milter.OnEndBody('E')
        self.assertTrue(self.user_t in resp[0])
        self.assertTrue("Plain text content" in resp[1])
        self.assertTrue('Invalid Content' not in resp[1])
        # check an inactive title
        self.milter.OnResetState()
        self.storage.set_status_alias(self.user_t, self.alias_t, status='inactive')
        resp = self.milter.OnRcptTo('R', self.alias_t, '')
        #d = Discard the message.
        self.assertEquals(resp, 'd')
        pass
