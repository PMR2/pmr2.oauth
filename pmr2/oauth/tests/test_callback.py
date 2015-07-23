import unittest

from Products.PloneTestCase import ptc

from pmr2.oauth.interfaces import ICallbackManager
from pmr2.oauth.callback import CallbackManager


class DummyToken(object):

    def __init__(self, callback):
        self.callback = callback


class DummyConsumer(object):

    def __init__(self, domain):
        self.domain = domain


class CallbackManagerTestCase(unittest.TestCase):
    """
    Test the validation method of the default callback manager.
    """

    def setUp(self):
        self.cbm = CallbackManager()

    def test_0000_faildata(self):
        consumer = DummyConsumer(None)
        callback = 'oob'
        self.assertFalse(self.cbm.validate(None, callback))
        self.assertFalse(self.cbm.validate(consumer, None))

    def test_0010_no_domain_oob(self):
        consumer = DummyConsumer(None)
        callback = 'oob'
        self.assertTrue(self.cbm.validate(consumer, callback))

    def test_0011_unequal(self):
        consumer = DummyConsumer('example.com')
        callback = 'http://test.example.com/oauth_callback'
        self.assertFalse(self.cbm.validate(consumer, callback))
        # Naturally an undefined callback cannot be equal to this.
        self.assertFalse(self.cbm.validate(consumer, None))

    def test_0012_equal(self):
        consumer = DummyConsumer('example.com')
        callback = 'http://example.com/oauth_callback'
        self.assertTrue(self.cbm.validate(consumer, callback))

    def test_0100_valid_subdomain(self):
        consumer = DummyConsumer('*.example.com')
        callback = 'http://test.example.com/oauth_callback'
        self.assertTrue(self.cbm.validate(consumer, callback))

    def test_0101_valid_port(self):
        consumer = DummyConsumer('example.com:8000')
        callback = 'http://example.com:8000/oauth_callback'
        self.assertTrue(self.cbm.validate(consumer, callback))

    def test_0102_valid_subdomain_port(self):
        consumer = DummyConsumer('*.example.com:8000')
        callback = 'http://test.example.com:8000/oauth_callback'
        self.assertTrue(self.cbm.validate(consumer, callback))

    def test_0110_invalid_subdomain(self):
        consumer = DummyConsumer('*.example.com')
        callback = 'http://testexample.com/oauth_callback'
        self.assertFalse(self.cbm.validate(consumer, callback))

        consumer = DummyConsumer('*example.com')
        callback = 'http://example.com/oauth_callback'
        self.assertFalse(self.cbm.validate(consumer, callback))

        consumer = DummyConsumer('example.com')
        callback = 'http://example.com:8000/oauth_callback'
        self.assertFalse(self.cbm.validate(consumer, callback))

        consumer = DummyConsumer('*.example.com:8')
        callback = 'http://test.example.com:8000/oauth_callback'
        self.assertFalse(self.cbm.validate(consumer, callback))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(CallbackManagerTestCase))
    return suite
