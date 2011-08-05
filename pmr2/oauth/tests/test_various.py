import time
import unittest

import zope.component

import oauth2

from pmr2.oauth.consumer import ConsumerManager
from pmr2.oauth.consumer import Consumer

from pmr2.oauth.utility import OAuthUtility

from pmr2.oauth import request

from pmr2.oauth.tests.base import TestRequest


class TestRequestAdapter(unittest.TestCase):

    def test_000_request(self):

        params = {
            'oauth_version': "1.0",
            'oauth_nonce': "4572616e48616d6d65724c61686176",
            'oauth_timestamp': "137131200",
            'oauth_consumer_key': "0685bd9184jfhq22",
            'oauth_signature_method': "HMAC-SHA1",
            'oauth_token': "ad180jjd733klru7",
            'oauth_signature': "wOJIO9A2W5mFwDgiDvZbTSMK%2FPY%3D",
        }

        req = TestRequest(oauth_keys=params)
        # Make sure our test request provide the oauth headers...
        self.assert_(req._auth.startswith('OAuth'))
        req = request.BrowserRequestAdapter(req)
        self.assert_(isinstance(req, oauth2.Request))
        self.assertEqual(req, params)

    def test_001_request(self):
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': "4572616e48616d6d65724c61686176",
            'oauth_timestamp': str(int(time.time())),
        }
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }
        consumer = oauth2.Consumer('consumer-key', 'consumer-secret')
        token = oauth2.Token('token-key', 'token-secret')
        req = TestRequest(form=form, oauth_keys=params)
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(params)
        answer.update(form)
        self.assertEqual(req, answer)


class TestUtility(unittest.TestCase):

    def test_000_Utility(self):
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': "4572616e48616d6d65724c61686176",
            'oauth_timestamp': int(time.time()),
            'oauth_consumer_key': "consumer-key",
            'oauth_token': "token-key",
        }
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }

        consumer = oauth2.Consumer(params['oauth_consumer_key'],
            'consumer-secret')
        token = oauth2.Token(params['oauth_token'], 'token-secret')

        req = TestRequest(oauth_keys=params)
        req = request.BrowserRequestAdapter(req)
        utility = OAuthUtility()
        # just testing so we are not signing anything...
        self.assertRaises(oauth2.MissingSignature,
            utility.verify_request, req, consumer, token)


class TestConsumer(unittest.TestCase):

    def setUp(self):
        pass
        #self.manager = ConsumerManager()

    def test_000_consumer(self):
        c = Consumer('consumer-key', 'consumer-secret')
        self.assertEqual(c.key, 'consumer-key')
        self.assertEqual(c.secret, 'consumer-secret')

    def test_100_consumer_manager_empty(self):
        m = ConsumerManager()
        self.assertEqual(m.get('consumer-key'), None)

    def test_101_consumer_manager_addget(self):
        m = ConsumerManager()
        c = Consumer('consumer-key', 'consumer-secret')
        m.add(c)
        result = m.get('consumer-key')
        self.assertEqual(result, c)

    def test_102_consumer_manager_doubleadd(self):
        m = ConsumerManager()
        c = Consumer('consumer-key', 'consumer-secret')
        m.add(c)
        self.assertRaises(ValueError, m.add, c)

    def test_102_consumer_manager_remove(self):
        m = ConsumerManager()
        c1 = Consumer('consumer-key', 'consumer-secret')
        c2 = Consumer('consumer-key2', 'consumer-secret')
        m.add(c1)
        m.add(c2)
        m.remove(c1.key)
        m.remove(c2)
        self.assertEqual(len(m._consumers), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRequestAdapter))
    suite.addTest(makeSuite(TestUtility))
    suite.addTest(makeSuite(TestConsumer))
    return suite
