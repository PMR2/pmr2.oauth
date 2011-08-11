import time
import oauth2 as oauth

from persistent import Persistent
from BTrees.OOBTree import OOBTree

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable

import zope.interface
from zope.schema import fieldproperty

from pmr2.oauth.interfaces import IToken
from pmr2.oauth.interfaces import ITokenManager
from pmr2.oauth.factory import factory
from pmr2.oauth.utility import random_string


class TokenManager(Persistent, Contained):
    """\
    A basic token manager for the default layer.

    This manager provides the bare minimum functionality, currently it
    does not easily provide a way for users to check what tokens they
    have approved.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)
    zope.interface.implements(ITokenManager)
    
    def __init__(self):
        self._tokens = OOBTree()

    def add(self, token):
        assert IToken.providedBy(token)
        if self.get(token.key):
            raise ValueError('token %s already exists', token.key)
        self._tokens[token.key] = token

    def checkCallback(self, callback):
        """\
        Verify that the callback is what we accept.
        """

        # Not implemented yet
        return callback is not None

    def checkNonce(self, nonce):
        """\
        Verify that the nonce is unique.
        """

        # Not implemented yet
        return True

    def generateRequestToken(self, consumer, request):
        """\
        Generate request token from consumer and request.
        """

        key = random_string(24)
        secret = random_string(24)
        token = Token(key, secret)

        if not self.checkNonce(request.get('oauth_nonce')):
            raise ValueError('nonce has been used recently')

        if not self.checkNonce(request.get('oauth_nonce')):
            raise ValueError('nonce has been used recently')

        callback = request.get('oauth_callback')
        if not self.checkCallback(callback):
            raise ValueError('callback must be specified or set to `oob`')
        token.set_callback(callback)

        token.consumer_key = consumer.key
        token.timestamp = int(time.time())

        # I know I am taking a collision risk with this random string.
        self.add(token)
        return token

    def get(self, token_key, default=None):
        return self._tokens.get(token_key, default)

    def remove(self, token):
        if IToken.providedBy(token):
            token = token.key
        self._tokens.pop(token)

TokenManagerFactory = factory(TokenManager)


class Token(Persistent, oauth.Token):

    zope.interface.implements(IToken)

    key = fieldproperty.FieldProperty(IToken['key'])
    secret = fieldproperty.FieldProperty(IToken['secret'])
    callback = fieldproperty.FieldProperty(IToken['callback'])
    callback_confirmed = fieldproperty.FieldProperty(IToken['callback_confirmed'])
    verifier = fieldproperty.FieldProperty(IToken['verifier'])
    user = fieldproperty.FieldProperty(IToken['user'])
    consumer_key = fieldproperty.FieldProperty(IToken['consumer_key'])
    timestamp = fieldproperty.FieldProperty(IToken['timestamp'])
    scope = fieldproperty.FieldProperty(IToken['scope'])
