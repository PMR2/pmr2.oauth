import time
import unittest

import zope.component

from pmr2.oauth.consumer import ConsumerManager
from pmr2.oauth.consumer import Consumer

from pmr2.oauth.token import TokenManager
from pmr2.oauth.token import Token

from pmr2.oauth.interfaces import *

from pmr2.oauth.tests.base import TestRequest


class TestConsumer(unittest.TestCase):

    def setUp(self):
        pass

    def test_000_consumer(self):
        consumer = Consumer('consumer-key', 'consumer-secret')
        self.assertEqual(consumer.key, 'consumer-key')
        self.assertEqual(consumer.secret, 'consumer-secret')
        # Default should be no problem.
        self.assertTrue(consumer.validate())

        consumer = Consumer('consumer2-key', 'consumer-secret', u'A Consumer')
        self.assertEqual(consumer.key, 'consumer2-key')
        self.assertEqual(consumer.secret, 'consumer-secret')
        self.assertEqual(consumer.title, u'A Consumer')

    def test_001_consumer_equality(self):
        consumer = Consumer('consumer-key', 'consumer-secret')
        d = Consumer('consumer-key', 'consumer-secret', u'Test')
        # Titles don't factor into equality in terms of authorization
        # schemes.
        self.assertEqual(consumer, d)

    def test_100_consumer_manager_empty(self):
        m = ConsumerManager()
        self.assertEqual(m.get('consumer-key'), None)

    def test_101_consumer_manager_addget(self):
        m = ConsumerManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        m.add(consumer)
        result = m.get('consumer-key')
        self.assertEqual(result, consumer)

        consumer2 = Consumer('consumer2-key', 'consumer-secret', u'A Consumer')
        m.add(consumer2)
        result = m.get('consumer2-key')
        self.assertEqual(result, consumer2)
        self.assertEqual(result.title, consumer2.title)

    def test_102_consumer_manager_doubleadd(self):
        m = ConsumerManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        m.add(consumer)
        self.assertRaises(ValueError, m.add, consumer)

    def test_103_consumer_manager_remove(self):
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
        token = Token('token-key', 'token-secret')
        self.assertEqual(token.key, 'token-key')
        self.assertEqual(token.secret, 'token-secret')

    def test_010_token_set_verifier(self):
        token = Token('token-key', 'token-secret')
        token.set_verifier()
        verifier = token.verifier
        token.set_verifier()
        self.assertEqual(verifier, token.verifier)
        token.set_verifier(True)
        self.assertNotEqual(verifier, token.verifier)

    def test_011_token_set_verifier_specific(self):
        token = Token('token-key', 'token-secret')
        token.set_verifier('verify')
        self.assertEqual('verify', token.verifier)
        token.set_verifier()
        self.assertEqual('verify', token.verifier)

    def test_020_token_get_callback_url(self):
        token = Token('token-key', 'token-secret')
        token.set_callback('http://example.com/')
        token.set_verifier('foo')
        url = token.get_callback_url()
        a = 'http://example.com/?oauth_verifier=foo&oauth_token=token-key'
        self.assertEqual(url, a)

    def test_021_token_get_callback_url(self):
        token = Token('token-key', 'token-secret')
        token.set_callback('http://example.com/;bar;?bus=4')
        token.set_verifier('foo')
        url = token.get_callback_url()
        a = 'http://example.com/;bar;?bus=4&oauth_verifier=foo&' \
            'oauth_token=token-key'
        self.assertEqual(url, a)

    def test_100_token_manager_empty(self):
        m = TokenManager()
        self.assertEqual(m.get('token-key'), None)

    def test_101_token_manager_addget(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        m.add(token)
        result = m.get('token-key')
        self.assertEqual(result, token)
        result = m.get(token)
        self.assertEqual(result, token)

    def test_102_token_manager_doubleadd(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        m.add(token)
        self.assertRaises(ValueError, m.add, token)

    def test_103_token_manager_remove(self):
        m = TokenManager()
        t1 = Token('token-key', 'token-secret')
        t2 = Token('token-key2', 'token-secret')
        m.add(t1)
        m.add(t2)
        m.remove(t1.key)
        m.remove(t2)
        self.assertEqual(len(m._tokens), 1)

    def test_112_token_manager_addget_user(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        token.user = 'user'
        m.add(token)
        result = m.getTokensForUser('user')
        # only access tokens are tracked.
        self.assertEqual(result, [])

    def test_111_token_manager_addget_user(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        token.user = 'user'
        token.access = True
        m.add(token)
        result = m.getTokensForUser('user')
        self.assertEqual(result, [token])

    def test_113_token_manager_doubleadd_user(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        token.user = 'user'
        token.access = True
        m.add(token)
        self.assertRaises(ValueError, m.add, token)
        result = m.getTokensForUser('user')
        # should not result in double entry.
        self.assertEqual(result, [token])

    def test_114_token_manager_addremove_user(self):
        m = TokenManager()
        t1 = Token('token-key', 'token-secret')
        t1.user = 't1user'
        t1.access = True
        t2 = Token('token-key2', 'token-secret')
        t2.user = 't2user'
        t2.access = True
        m.add(t1)
        m.add(t2)
        self.assertEqual(m.getTokensForUser('user'), [])
        self.assertEqual(m.getTokensForUser('t1user'), [t1])
        self.assertEqual(m.getTokensForUser('t2user'), [t2])
        m.remove(t1.key)
        m.remove(t2)
        self.assertEqual(m.getTokensForUser('t1user'), [])
        self.assertEqual(m.getTokensForUser('t2user'), [])

    def test_115_token_manager_user_inconsistency(self):
        m = TokenManager()
        t1 = Token('token-key', 'token-secret')
        t1.user = 't1user'
        t1.access = True
        t2 = Token('token-key2', 'token-secret')
        t2.user = 't2user'
        t2.access = True
        m.add(t1)
        m.add(t2)
        m._del_user_map(t2)
        # User must know about the token for the getter to work.
        self.assertEqual(m.getTokensForUser('t2user'), [])

    def test_120_token_manager_access_token_tm_empty(self):
        m = TokenManager()
        self.assertRaises(TokenInvalidError, m.getAccessToken, 'token-key')
        self.assertRaises(TokenInvalidError, m.getRequestToken, 'token-key')
        self.assertEqual(m.getAccessToken('token-key', None), None)

    def test_121_token_manager_access_token_get_not_access(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        m.add(token)
        self.assertRaises(NotAccessTokenError, m.getAccessToken, 'token-key')
        self.assertEqual(m.getRequestToken('token-key'), token)

    def test_122_token_manager_access_token_get_user_no_access(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        token.user = 'user'
        m.add(token)
        self.assertRaises(NotAccessTokenError, m.getAccessToken, 'token-key')
        self.assertEqual(m.getRequestToken('token-key'), token)

    def test_123_token_manager_access_token_get_access_no_user(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        token.access = True
        m.add(token)
        self.assertRaises(TokenInvalidError, m.getAccessToken, 'token-key')
        self.assertRaises(NotRequestTokenError, m.getRequestToken, 'token-key')

    def test_124_token_manager_access_token_get_access(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        token.access = True
        token.user = 'user'
        m.add(token)
        self.assertEqual(m.getAccessToken('token-key'), token)
        self.assertRaises(NotRequestTokenError, m.getRequestToken, 'token-key')

    def test_125_token_manager_access_token_inconsistent_fail(self):
        m = TokenManager()
        token = Token('token-key', 'token-secret')
        token.access = True
        m.add(token)
        # this would result in the token not being indexed.
        token.user = 'user'
        self.assertRaises(TokenInvalidError, m.getAccessToken, 'token-key')
        self.assertRaises(NotRequestTokenError, m.getRequestToken, 'token-key')

    def test_200_token_manager_generate_request_token(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        callback = 'oob'
        token = m.generateRequestToken(consumer.key, callback)
        self.assertEqual(m.get(token.key), token)
        self.assertEqual(m.get(token.key).consumer_key, consumer.key)
        self.assertEqual(m.get(token.key).access, False)
        self.assertEqual(m.getRequestToken(token.key).key, token.key)

    def test_201_token_manager_generate_request_token_no_callback(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        self.assertRaises(CallbackValueError, m.generateRequestToken, 
            consumer.key, None)

    def test_250_token_manager_claim(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        callback = 'oob'
        token = m.generateRequestToken(consumer.key, callback)
        m.claimRequestToken(token, 'user')
        self.assertEqual(token.user, 'user')
        self.assertTrue(token.expiry > int(time.time()))

    def test_251_token_manager_claim_fail_access(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        callback = 'oob'
        token = m.generateRequestToken(consumer.key, callback)
        token.access = True  # hack it to be access token.
        self.assertRaises(TokenInvalidError, m.claimRequestToken, token, 'u')
        self.assertEqual(token.user, None)

    def test_252_token_manager_claim_fail_missing(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        callback = 'oob'
        token = m.generateRequestToken(consumer.key, callback)
        m.remove(token)  # remove it
        self.assertRaises(TokenInvalidError, m.claimRequestToken, token, 'u')
        self.assertEqual(token.user, None)

    def test_300_token_manager_generate_access_token(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        callback = 'oob'
        server_token = m.generateRequestToken(consumer.key, callback)
        verifier = server_token.verifier

        # Also simulate user claiming the token
        m.claimRequestToken(server_token.key, 'user')

        # now simulate passing only the key and secret to consumer
        request_token = Token(server_token.key, server_token.secret)
        token = m.generateAccessToken(consumer.key, request_token.key)

        self.assertEqual(m.get(token.key), token)
        self.assertEqual(m.get(token.key).consumer_key, consumer.key)
        self.assertEqual(m.get(token.key).access, True)
        self.assertEqual(m.get(token.key).user, 'user')

        # Also, assert that this token key is available in the method
        # that returns these keys by user id.
        self.assertEqual(m.getTokensForUser('user'), [token])

    def test_310_token_manager_generate_access_token_no_user(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        callback = 'oob'
        server_token = m.generateRequestToken(consumer.key, callback)

        # simulate passing only the key and secret to consumer
        request_token = Token(server_token.key, server_token.secret)

        # However, it's not claimed by a user yet, so expiry is not set,
        # thus...
        self.assertRaises(TokenInvalidError, m.generateAccessToken, 
            consumer.key, request_token.key)

    def test_311_token_manager_generate_access_token_no_request_token(self):
        m = TokenManager()
        consumer = Consumer('consumer-key', 'consumer-secret')
        self.assertRaises(TokenInvalidError, m.generateAccessToken, 
            consumer.key, None)

    def test_500_token_manager_get_dummy(self):
        m = TokenManager()
        token = m.get(m.DUMMY_KEY)
        self.assertEqual(token.secret, m.DUMMY_SECRET)
        # Now this is where it might get a bit interesting.  For dealing
        # with dummy tokens, is it better to generate a new one, or just
        # store it and provide one to ensure constant time?  Either way,
        # if somehow the dummy is removed, the utility shouldn't have to
        # die in a fire.
        m.remove(token)
        token = m.get(m.DUMMY_KEY)
        self.assertEqual(token, None)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestConsumer))
    suite.addTest(makeSuite(TestToken))
    return suite
