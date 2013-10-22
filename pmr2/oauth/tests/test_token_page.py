import time
import unittest
from urlparse import parse_qsl

import zope.component

from zExceptions import Forbidden
from zExceptions import BadRequest
from zExceptions import Unauthorized
from Products.PloneTestCase import ptc

from pmr2.oauth.interfaces import ITokenManager, IConsumerManager
from pmr2.oauth.interfaces import IScopeManager
from pmr2.oauth.token import Token
from pmr2.oauth.consumer import Consumer
from pmr2.oauth.browser import consumer
from pmr2.oauth.browser import token
from pmr2.oauth.browser import user

from pmr2.oauth.tests.base import makeToken
from pmr2.oauth.tests.base import TestRequest
from pmr2.oauth.tests.base import SignedTestRequest


class TokenPageTestCase(ptc.PloneTestCase):
    """
    Testing functionalities of forms that don't fit well into doctests.
    """

    def afterSetUp(self):
        request = TestRequest()
        self.consumerManager = zope.component.getMultiAdapter(
            (self.portal, request), IConsumerManager)
        self.consumer = Consumer('consumer.example.com', 'consumer-secret')
        self.consumerManager.add(self.consumer)

        self.tokenManager = zope.component.getMultiAdapter(
            (self.portal, request), ITokenManager)

        self.scopeManager = zope.component.getMultiAdapter(
            (self.portal, request), IScopeManager)

        self.reqtoken = self.tokenManager.generateRequestToken(
            self.consumer.key, 'oob')
        self.scopeManager.requestScope(self.reqtoken.key, None)

    def test_request_token_page_fail(self):
        request = TestRequest()
        rt = token.RequestTokenPage(self.portal, request)
        self.assertRaises(BadRequest, rt)

    def test_request_token_page_good(self):
        baseurl = self.portal.absolute_url()
        timestamp = str(int(time.time()))
        request = SignedTestRequest(
            timestamp=timestamp,
            consumer=self.consumer,
            callback=baseurl + '/test_oauth_callback',
        )
        qs = dict(parse_qsl(token.RequestTokenPage(self.portal, request)()))
        self.assertEqual(
            self.tokenManager.getRequestToken(qs['oauth_token']).secret,
            qs['oauth_token_secret'],
        )

    def test_access_token_page_fail(self):
        request = TestRequest()
        rt = token.GetAccessTokenPage(self.portal, request)
        self.assertRaises(BadRequest, rt)

    def test_access_token_page_good(self):
        self.reqtoken.user = 'test_user_1_'
        baseurl = self.portal.absolute_url()
        timestamp = str(int(time.time()))
        request = SignedTestRequest(
            timestamp=timestamp,
            consumer=self.consumer,
            token=self.reqtoken,
            verifier=self.reqtoken.verifier,
        )
        page = token.GetAccessTokenPage(self.portal, request)
        qs = dict(parse_qsl(page()))
        self.assertEqual(
            self.tokenManager.getAccessToken(qs['oauth_token']).secret,
            qs['oauth_token_secret'],
        )

        # Can't re-request as request token should have been removed.
        self.assertTrue(
            self.tokenManager.getRequestToken(self.reqtoken.key, None) is None)
        self.assertTrue(
            self.scopeManager.getScope(self.reqtoken.key, None) is None)
        self.assertRaises(Unauthorized, page)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TokenPageTestCase))
    return suite
