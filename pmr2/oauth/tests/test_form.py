import unittest

import zope.component

from zExceptions import Unauthorized
from Products.PloneTestCase import ptc
from Products.PloneTestCase.ptc import default_user

from pmr2.oauth.interfaces import ITokenManager, IConsumerManager
from pmr2.oauth.interfaces import IScopeManager
from pmr2.oauth.token import Token
from pmr2.oauth.consumer import Consumer
from pmr2.oauth.browser import consumer
from pmr2.oauth.browser import token
from pmr2.oauth.browser import user

from pmr2.oauth.tests.base import TestRequest


class FormTestCase(ptc.PloneTestCase):
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

    def test_0000_authform_render(self):
        request = TestRequest(form={
            'oauth_token': self.reqtoken.key,
        })
        form = token.AuthorizeTokenForm(self.portal, request)
        form.update()
        result = form.render()
        self.assertTrue('_authenticator' in result)

    def test_0001_authform_post_authfail(self):
        request = TestRequest(form={
            'oauth_token': self.reqtoken.key,
            'form.buttons.approve': 1,
        })
        # simulate lack of CSRF
        request.form['_authenticator'] = None
        form = token.AuthorizeTokenForm(self.portal, request)
        self.assertRaises(Unauthorized, form.update)

    def test_0002_authform_post_authgood(self):
        request = TestRequest(form={
            'oauth_token': self.reqtoken.key,
            'form.buttons.approve': 1,
        })
        form = token.AuthorizeTokenForm(self.portal, request)
        form.update()
        result = form.render()
        self.assertTrue(self.reqtoken.verifier in result)

    def test_1000_consumermanageform_fail(self):
        request = TestRequest(form={
            'form.buttons.remove': 1,
        })
        request.form['_authenticator'] = None
        form = consumer.ConsumerManageForm(self.portal, request)
        self.assertRaises(Unauthorized, form.update)

    def test_2000_usertokenform_fail(self):
        # have to add a token to show the button.
        atok = self.tokenManager._generateBaseToken(self.consumer.key)
        atok.access = True
        atok.user = default_user
        self.tokenManager.add(atok)

        request = TestRequest(form={
            'form.buttons.revoke': 1,
        })
        request.form['_authenticator'] = None
        form = user.UserTokenForm(self.portal, request)
        self.assertRaises(Unauthorized, form.update)

    def test_2100_usertokenform_revoke(self):
        # have to add a token to show the button.
        atok = self.tokenManager._generateBaseToken(self.consumer.key)
        atok.access = True
        atok.user = default_user
        self.tokenManager.add(atok)

        self.login(default_user)
        request = TestRequest()
        form = user.UserTokenForm(self.portal, request)
        result = form()
        self.assertTrue(atok.key in result)
        self.assertTrue('Revoke' in result)

        request = TestRequest(form={
            'form.widgets.key': [atok.key],
            'form.buttons.revoke': 1,
        })
        form = user.UserTokenForm(self.portal, request)
        result = form()
        self.assertFalse(atok.key in result)
        # Ideally this would not be rendered, but it is, due to how the
        # button and handler are coupled together.  If the button is not
        # available the action wouldn't be executed, which would have
        # meant that the token wouldn't be revoked...

        # This whole issue can probably be sidestepped with a redirect.
        # self.assertFalse('Revoke' in result)

    def test_2200_usertokenform_no_token_no_button(self):
        # have to add a token to show the button.
        request = TestRequest()
        form = user.UserTokenForm(self.portal, request)
        self.assertFalse('Revoke' in form())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(FormTestCase))
    return suite
