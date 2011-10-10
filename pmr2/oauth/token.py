import time
import urlparse
import oauth2 as oauth

from persistent import Persistent
from BTrees.OOBTree import OOBTree

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable

import zope.interface
from zope.schema import fieldproperty

from pmr2.oauth.interfaces import IToken
from pmr2.oauth.interfaces import ITokenManager
from pmr2.oauth.interfaces import CallbackValueError
from pmr2.oauth.interfaces import TokenInvalidError
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

    def _generateBaseToken(self, consumer, request):
        if not self.checkNonce(request.get('oauth_nonce')):
            raise ValueError('nonce has been used recently')

        key = random_string(24)
        secret = random_string(24)
        token = Token(key, secret)
        token.consumer_key = consumer.key
        token.timestamp = int(time.time())
        return token

    def generateRequestToken(self, consumer, request):
        """\
        Generate request token from consumer and request.
        """

        token = self._generateBaseToken(consumer, request)
        callback = request.get('oauth_callback')
        if not self.checkCallback(callback):
            raise CallbackValueError(
                'callback must be specified or set to `oob`')
        token.set_callback(callback)
        token.set_verifier()

        # I know I am taking a collision risk with this random string.
        self.add(token)
        return token

    def generateAccessToken(self, consumer, request):
        if not self.tokenRequestVerify(request=request):
            raise TokenInvalidError('invalid token')
        old_key = request.get('oauth_token')
        old_token = self.get(old_key)
        
        token = self._generateBaseToken(consumer, request)
        token.access = True
        token.user = old_token.user

        # Terminate old token to prevent reuse.
        self.remove(old_key)
        self.add(token)

        return token

    def get(self, token_key, default=None):
        return self._tokens.get(token_key, default)

    def remove(self, token):
        if IToken.providedBy(token):
            token = token.key
        self._tokens.pop(token)

    def tokenRequestVerify(self, request=None):
        """\
        Verify that the request results in a valid token.
        """

        token_key = request.get('oauth_token')
        token = self.get(token_key)
        if token is None:
            return False
        return token.verifier == request.get('oauth_verifier')

TokenManagerFactory = factory(TokenManager)


class Token(Persistent, oauth.Token):

    zope.interface.implements(IToken)

    key = fieldproperty.FieldProperty(IToken['key'])
    secret = fieldproperty.FieldProperty(IToken['secret'])
    callback = fieldproperty.FieldProperty(IToken['callback'])
    callback_confirmed = fieldproperty.FieldProperty(
        IToken['callback_confirmed'])
    verifier = fieldproperty.FieldProperty(IToken['verifier'])
    access = fieldproperty.FieldProperty(IToken['access'])

    user = fieldproperty.FieldProperty(IToken['user'])
    consumer_key = fieldproperty.FieldProperty(IToken['consumer_key'])
    timestamp = fieldproperty.FieldProperty(IToken['timestamp'])
    scope_id = fieldproperty.FieldProperty(IToken['scope_id'])
    scope_value = fieldproperty.FieldProperty(IToken['scope_value'])

    def set_verifier(self, verifier=None):
        """\
        Differs from original implementation.
        
        This uses the random_string method to generate the verifier key.
        Does not regenerate a new key if verifier is already set, unless
        a specific verifier is specified which will the be set.  To
        generate a new random value, set the verifier parameter to True.
        """

        if verifier is True or (verifier is None and self.verifier is None):
            # As the user could hit back or whatever reason and reload
            # the key before the consumer gets to complete the request,
            # and to simplify how this is invoked by the authorization
            # form, we only generate this once, unless the caller really
            # wants to do this.
            self.verifier = random_string(24)
            return

        if verifier is not None:
            # fieldproperty should validate this input automatically.
            self.verifier = verifier

    def get_callback_url(self):
        """\
        Original was broken.
        """

        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            q = query and [query] or []
            q.append('oauth_verifier=%s' % self.verifier)
            q.append('oauth_token=%s' % self.key)
            query = '&'.join(q)
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

