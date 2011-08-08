import zope.component
from zope.publisher.interfaces.browser import IBrowserRequest
from time import time
import unittest
from zExceptions import Redirect

from pmr2.oauth.interfaces import *
from pmr2.oauth.request import BrowserRequestAdapter


class TestExtraction(unittest.TestCase):

    params = {
        'oauth_version': "1.0",
        'oauth_nonce': "4572616e48616d6d65724c61686176",
        'oauth_timestamp': "137131200",
        'oauth_consumer_key': "0685bd9184jfhq22",
        'oauth_signature_method': "HMAC-SHA1",
        'oauth_token': "ad180jjd733klru7",
        'oauth_signature': "wOJIO9A2W5mFwDgiDvZbTSMK%2FPY%3D",
    }

    def setUp(self):
        self.plugin = self.createPlugin()
        zope.component.provideAdapter(
            BrowserRequestAdapter, (IBrowserRequest,), IRequest)

    def createPlugin(self):
        from pmr2.oauth.tests.utility import MockPAS
        from pmr2.oauth.tests.utility import MockSite
        from pmr2.oauth.plugins.oauth import OAuthPlugin
        plugin = OAuthPlugin("oauth")
        return plugin.__of__((MockPAS()).__of__(MockSite()))

    def testEmptyExtraction(self):
        plugin = self.plugin
        creds = plugin.extractCredentials(plugin.REQUEST)
        self.assertEqual(creds, {})


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestExtraction))
    return suite
