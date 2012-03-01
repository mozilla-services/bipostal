import unittest
from StringIO import StringIO
from bipostmap import ResolveServer


class FakeSocket(StringIO):

    def makefile(self):
        return self

class TestMilter(unittest.TestCase):

    def setUp(self):
        self.server = ResolveServer(None, {'backend': 'bipostal.storage.mem.Storage'})
        self.server.storage.db = {'a@b.c-None': {'email': 'active@example.com',
                                                      'status': 'active',
                                                      'alias': 'a@b.c'},
                                  'b@b.c-None': {'email': 'inactive@example.com',
                                                      'status': 'inactive',
                                                      'alias': 'b@b.c'},
                                  'c@b.c-None': {'email': 'deleted@example.com',
                                                      'status': 'deleted',
                                                      'alias': 'c@b.c'}}
                                            

    def tearDown(self):
        pass

    def test_all(self):
        fake = FakeSocket('GET a@b.c\n')
        self.server.handle(fake, None)
        value = fake.getvalue()
        self.failUnless('200 ' in value and 'active@example.com' in value)
        fake = FakeSocket('GET b@b.c\n')
        self.server.handle(fake, None)
        value = fake.getvalue()
        self.failUnless('200 ' in value and 'inactive@example.com' in value)
        fake = FakeSocket('GET c@b.c\n')
        self.server.handle(fake, None)
        value = fake.getvalue()
        self.failUnless('500 ' in value)

