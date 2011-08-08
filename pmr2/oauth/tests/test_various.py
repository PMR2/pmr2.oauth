import time
import unittest

import zope.component

import oauth2 as oauth

from pmr2.oauth.consumer import ConsumerManager
from pmr2.oauth.consumer import Consumer

from pmr2.oauth.token import TokenManager
from pmr2.oauth.token import Token

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
        self.assert_(isinstance(req, oauth.Request))
        self.assertEqual(req, params)

    def test_001_request_form(self):
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': "4572616e48616d6d65724c61686176",
            'oauth_timestamp': str(int(time.time())),
        }
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form, oauth_keys=params)
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(params)
        answer.update(form)
        self.assertEqual(req, answer)

    def test_002_request_basic_auth(self):
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form)
        req._auth = 'Basic ' + 'test:test'.encode('base64')
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(form)
        self.assertEqual(req, answer)

    def test_003_request_noauth(self):
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form)
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(form)
        self.assertEqual(req, answer)

    def test_010_request_noform(self):
        form = {}
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form)
        req = request.BrowserRequestAdapter(req)
        answer = {}
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

        consumer = oauth.Consumer(params['oauth_consumer_key'],
            'consumer-secret')
        token = oauth.Token(params['oauth_token'], 'token-secret')

        req = TestRequest(oauth_keys=params)
        req = request.BrowserRequestAdapter(req)
        utility = OAuthUtility()
        # just testing so we are not signing anything...
        self.assertRaises(oauth.MissingSignature,
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


class TestToken(unittest.TestCase):

    def setUp(self):
        pass
        #self.manager = ConsumerManager()

    def test_000_token(self):
        c = Token('token-key', 'token-secret')
        self.assertEqual(c.key, 'token-key')
        self.assertEqual(c.secret, 'token-secret')

    def test_100_token_manager_empty(self):
        m = TokenManager()
        self.assertEqual(m.get('token-key'), None)

    def test_101_token_manager_addget(self):
        m = TokenManager()
        c = Token('token-key', 'token-secret')
        m.add(c)
        result = m.get('token-key')
        self.assertEqual(result, c)

    def test_102_token_manager_doubleadd(self):
        m = TokenManager()
        c = Token('token-key', 'token-secret')
        m.add(c)
        self.assertRaises(ValueError, m.add, c)

    def test_102_token_manager_remove(self):
        m = TokenManager()
        t1 = Token('token-key', 'token-secret')
        t2 = Token('token-key2', 'token-secret')
        m.add(t1)
        m.add(t2)
        m.remove(t1.key)
        m.remove(t2)
        self.assertEqual(len(m._tokens), 0)

    def test_200_token_manager_generate_request_token(self):
        m = TokenManager()
        c = Consumer('consumer-key', 'consumer-secret')
        r = oauth.Request.from_consumer_and_token(c, None)
        r['oauth_callback'] = u'oob'
        token = m.generateRequestToken(c, r)
        self.assertEqual(len(m._tokens), 1)
        self.assertEqual(m.get(token.key), token)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRequestAdapter))
    suite.addTest(makeSuite(TestUtility))
    suite.addTest(makeSuite(TestConsumer))
    suite.addTest(makeSuite(TestToken))
    return suite
