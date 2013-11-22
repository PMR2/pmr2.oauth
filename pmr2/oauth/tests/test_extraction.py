from zope.interface import Interface
import zope.component
from time import time
import unittest

from zExceptions import Forbidden
from zExceptions import BadRequest

from pmr2.oauth.interfaces import *

from pmr2.oauth.utility import SiteRequestValidatorAdapter

from pmr2.oauth.token import Token
from pmr2.oauth.token import TokenManager

from pmr2.oauth.consumer import Consumer
from pmr2.oauth.consumer import ConsumerManager

from pmr2.oauth.tests.base import IOAuthTestLayer
from pmr2.oauth.tests.base import TestRequest
from pmr2.oauth.tests.base import SignedTestRequest

from pmr2.oauth.tests.adapter import TestCallbackManager


def mock_factory(cls):
    instance = cls()
    def getInstance(context, request):
        return instance
    return getInstance


class TestExtraction(unittest.TestCase):

    default_consumer_key = 'consumer.example.com'
    default_user_id = 'test_user'

    def setUp(self):
        tmf = mock_factory(TokenManager)
        cmf = mock_factory(ConsumerManager)
        self.plugin = self.createPlugin()
        zope.component.provideAdapter(
            cmf, (Interface, IOAuthTestLayer,), IConsumerManager)
        zope.component.provideAdapter(
            tmf, (Interface, IOAuthTestLayer,), ITokenManager)
        zope.component.provideAdapter(
            TestCallbackManager, (Interface, IOAuthTestLayer), ICallbackManager)
        zope.component.provideAdapter(SiteRequestValidatorAdapter,
            (Interface, IOAuthTestLayer,), IOAuthRequestValidatorAdapter)

        self.consumerManager = zope.component.getMultiAdapter(
            (object, TestRequest()), IConsumerManager)
        self.tokenManager = zope.component.getMultiAdapter(
            (object, TestRequest()), ITokenManager)
        self.callbackManager = zope.component.getMultiAdapter(
            (object, TestRequest()), ICallbackManager)

    def createPlugin(self):
        from pmr2.oauth.tests.utility import MockPAS
        from pmr2.oauth.tests.utility import MockSite
        from pmr2.oauth.plugins.oauth import OAuthPlugin

        class NoScopeOAuthPlugin(OAuthPlugin):
            def _validateScope(self, *a, **kw):
                return True

        plugin = NoScopeOAuthPlugin("oauth")
        return plugin.__of__((MockPAS()).__of__(MockSite()))

    def generate_consumer_and_token(self, consumer_key=None,
            save_consumer=False, save_token=False):
        if not consumer_key:
            consumer_key = self.default_consumer_key
        consumer = Consumer('consumer.example.com', 'consumer-secret')
        token = Token('token-key', 'token-secret')
        token.access = True
        token.user = self.default_user_id
        token.consumer_key = 'consumer.example.com'
        if save_consumer:
            self.consumerManager.add(consumer)
        if save_token:
            self.tokenManager.add(token)
        return consumer, token

    def save_consumer_and_token(self, consumer_key=None):
        return self.generate_consumer_and_token(consumer_key, True, True)

    def test_0000_empty_extraction(self):
        plugin = self.plugin
        creds = plugin.extractCredentials(plugin.REQUEST)
        self.assertEqual(creds, {})

    def test_0100_fail_missing_unsigned_token(self):
        plugin = self.plugin
        timestamp = str(int(time()))
        request = TestRequest(
            oauth_keys={
                'oauth_token': "nosuchtoken",
                'oauth_version': "1.0",
                'oauth_nonce': "fakenonce",
                'oauth_timestamp': timestamp,
            },
        )
        self.assertRaises(BadRequest, plugin.extractCredentials, request)

    def test_0200_fail_unsigned_request(self):
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()

        timestamp = str(int(time()))
        request = TestRequest(
            oauth_keys={
                'oauth_consumer_key': consumer.key,
                'oauth_token': token.key,
                'oauth_version': "1.0",
                'oauth_nonce': "fakenonce",
                'oauth_timestamp': timestamp,
            },
        )
        self.assertRaises(BadRequest, plugin.extractCredentials, request)

    def test_0201_fail_badly_signed_request(self):
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()

        timestamp = str(int(time()))
        request = TestRequest(
            oauth_keys={
                'oauth_consumer_key': consumer.key,
                'oauth_token': token.key,
                'oauth_version': "1.0",
                'oauth_nonce': "fakenonce",
                'oauth_timestamp': timestamp,
                'oauth_signature_method': "HMAC-SHA1",
                'oauth_signature': "badsignature",
                'oauth_body_hash': "2jmj7l5rSw0yVb%2FvlWAYkK/YBwk=", 
            },
        )
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_0202_fail_bad_timestamp(self):
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()

        timestamp = '0'
        request = SignedTestRequest(consumer=consumer, token=token,
            timestamp=timestamp)
        self.assertRaises(BadRequest, plugin.extractCredentials, request)

    def test_0210_fail_signed_mismatch_both_secrets(self):
        plugin = self.plugin
        real_consumer, real_token = self.save_consumer_and_token()
        consumer, token = self.generate_consumer_and_token()
        consumer.secret = 'failfailfailfail'
        token.secret = 'failfailfailfail'

        request = SignedTestRequest(consumer=consumer, token=token,)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_0211_fail_signed_mismatch_consumer_secret(self):
        plugin = self.plugin
        real_consumer, real_token = self.save_consumer_and_token()
        consumer, token = self.generate_consumer_and_token()
        consumer.secret = 'failfailfailfail'
        token = real_token

        request = SignedTestRequest(consumer=consumer, token=token,)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_0212_fail_signed_mismatch_token_secret(self):
        plugin = self.plugin
        real_consumer, real_token = self.save_consumer_and_token()
        consumer, token = self.generate_consumer_and_token()
        token.secret = 'failfailfailfail'
        consumer = real_consumer

        request = SignedTestRequest(consumer=consumer, token=token,)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_0300_fail_request_token(self):
        plugin = self.plugin
        consumer, atoken = self.generate_consumer_and_token(save_consumer=True)
        # make request token
        token = self.tokenManager.generateRequestToken(consumer.key, 
            'http://callback.example.com/')

        # Request token generated properly and stored, but verifier not
        # signed and provided with request.
        request = SignedTestRequest(consumer=consumer, token=token,)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

        # Verifier provided, but no users have claimed this token.
        request = SignedTestRequest(consumer=consumer, token=token, 
            verifier=token.verifier)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_0301_success_request_token(self):
        plugin = self.plugin
        consumer, atoken = self.generate_consumer_and_token(save_consumer=True)
        # make request token
        token = self.tokenManager.generateRequestToken(consumer.key, 
            'http://callback.example.com/')

        # have a user claim this.
        self.tokenManager.claimRequestToken(token, 'user')

        # Request token generated properly and stored, with verifier
        # signed and provided with request, and a user has claimed the
        # token.
        request = SignedTestRequest(url='http://127.0.0.1/OAuthGetAccessToken',
            consumer=consumer, token=token, verifier=token.verifier)

        # Credentials successfully not returned.
        self.assertEqual(plugin.extractCredentials(request), {})

        # Try again using query parameters. (3.5.3)
        request = SignedTestRequest(url='http://127.0.0.1/OAuthGetAccessToken',
            consumer=consumer, token=token, verifier=token.verifier,
            signature_type='QUERY')

        # Credentials successfully not returned.
        self.assertEqual(plugin.extractCredentials(request), {})

        # Now if the generated request token was removed from the store,
        # this same token request would be forbidden.
        request = SignedTestRequest(consumer=consumer, token=token,)
        self.tokenManager.remove(token)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

        # Since atoken isn't saved either, it should have failed too.
        request = SignedTestRequest(consumer=consumer, token=atoken,)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_0500_fail_access_token_no_consumer(self):
        # use request token
        plugin = self.plugin
        consumer, token = self.generate_consumer_and_token(save_token=True)
        request = SignedTestRequest(consumer=consumer, token=token,)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_1000_success_access_token(self):
        # use request token
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()

        request = SignedTestRequest(consumer=consumer, token=token,)
        credentials = plugin.extractCredentials(request)
        self.assertEqual(credentials['userid'], self.default_user_id)

    def test_1001_success_access_token_3_5_3(self):
        # use request token
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()

        request = SignedTestRequest(consumer=consumer, token=token,
            signature_type='QUERY')
        credentials = plugin.extractCredentials(request)
        self.assertEqual(credentials['userid'], self.default_user_id)

    def test_1050_success_with_www_form_body(self):
        # use request token
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()
        request = SignedTestRequest(consumer=consumer, token=token,
            method='POST', raw_body='title=test&value=1',
            CONTENT_TYPE='application/x-www-form-urlencoded')
        credentials = plugin.extractCredentials(request)
        self.assertEqual(credentials['userid'], self.default_user_id)

    def test_1100_missing_token_ignored(self):
        # Should not forbid cases where the oauth_token is missing (it
        # could be a RequestToken, let that page handle it).
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()

        request = SignedTestRequest(consumer=consumer, callback='oob')
        credentials = plugin.extractCredentials(request)
        self.assertEqual(credentials, {})

    def test_1101_strip_access_token_failure(self):
        # Should not forbid cases where the oauth_token is a request
        # token, as it could be used to request for an access token.
        # (at least this is a valid token, just has no credentials).
        plugin = self.plugin
        consumer, token = self.save_consumer_and_token()

        # forcibily strip that token's access rights.
        token.access = False

        request = SignedTestRequest(consumer=consumer, token=token,)
        self.assertRaises(Forbidden, plugin.extractCredentials, request)

    def test_2000_base_oauth_adapter(self):
        oauth1 = zope.component.getMultiAdapter(
            (object, TestRequest()), IOAuthRequestValidatorAdapter)
        self.assertEqual(oauth1.dummy_request_token,
            self.tokenManager.DUMMY_KEY)
        self.assertEqual(oauth1.dummy_access_token,
            self.tokenManager.DUMMY_KEY)

        # should still work if purged.
        self.tokenManager.remove(self.tokenManager.DUMMY_KEY)
        self.assertEqual(oauth1.dummy_request_token,
            self.tokenManager.DUMMY_KEY)
        self.assertEqual(oauth1.dummy_access_token,
            self.tokenManager.DUMMY_KEY)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestExtraction))
    return suite
