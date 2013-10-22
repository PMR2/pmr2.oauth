import time
import urlparse

from persistent import Persistent
from persistent.list import PersistentList
from BTrees.OOBTree import OOBTree

from zope.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable

import zope.interface
from zope.schema import fieldproperty

from pmr2.oauth.interfaces import IToken
from pmr2.oauth.interfaces import ITokenManager
from pmr2.oauth.interfaces import CallbackValueError
from pmr2.oauth.interfaces import TokenInvalidError, ExpiredTokenError
from pmr2.oauth.interfaces import NotAccessTokenError, NotRequestTokenError
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

    DUMMY_KEY = 'dummy'
    DUMMY_SECRET = 'dummy'

    # expiry
    claim_timeout = 180
    
    def __init__(self):
        self._tokens = OOBTree()
        self._user_token_map = OOBTree()
        dummy = self._makeDummy()
        self.add(dummy)

    def _makeDummy(self):
        dummy = Token(self.DUMMY_KEY, self.DUMMY_SECRET)
        return dummy

    def _add_user_map(self, token):
        if not token.access or token.user is None:
            return

        # only tracking access tokens with user defined.
        user_tokens = self._user_token_map.get(token.user, None)
        if user_tokens is None:
            user_tokens = PersistentList()
            self._user_token_map[token.user] = user_tokens

        user_tokens.append(token.key)

    def _del_user_map(self, token):
        if token.user is None:
            return

        # only tracking access tokens with user defined.
        user_tokens = self._user_token_map.get(token.user, None)
        if user_tokens is None:
            # guess this user didn't have any tokens tracked before.
            return

        if token.key in user_tokens:
            # Well this key may not have been mapped.
            user_tokens.remove(token.key)

    def add(self, token):
        assert IToken.providedBy(token)
        if self.get(token.key):
            raise ValueError('token %s already exists', token.key)
        self._tokens[token.key] = token
        self._add_user_map(token)

    def _generateBaseToken(self, consumer_key):
        key = random_string(24)
        secret = random_string(24)
        token = Token(key, secret)
        token.consumer_key = consumer_key
        token.timestamp = int(time.time())
        return token

    def generateRequestToken(self, consumer_key, callback):
        """\
        Generate request token from consumer and request.
        """

        # This is our constraint.
        if callback is None:
            raise CallbackValueError(
                'callback must be specified or set to `oob`')

        token = self._generateBaseToken(consumer_key)
        token.set_callback(callback)
        token.set_verifier()

        token.expiry = int(time.time()) + self.claim_timeout

        self.add(token)
        return token

    def generateAccessToken(self, consumer_key, request_token):

        # Get the copy that is being tracked here.
        old_token = self.get(request_token)
        if not old_token:
            raise TokenInvalidError('invalid token')
        old_key = old_token.key

        token = self._generateBaseToken(consumer_key)
        token.access = True

        # Must have a user.
        if not old_token.user:
            raise TokenInvalidError('token has no user')
        token.user = old_token.user

        # Now add token.
        self.add(token)
        return token

    def claimRequestToken(self, token, user):
        token = self.get(token)
        if not token:
            raise TokenInvalidError('invalid token')
        if token.access:
            raise TokenInvalidError('not request token')
        token.user = user
        token.expiry = int(time.time()) + self.claim_timeout

    def get(self, token, default=None):
        token_key = IToken.providedBy(token) and token.key or token
        return self._tokens.get(token_key, default)

    def getRequestToken(self, token, default=False):
        token = self.get(token, default)
        if token is default:
            if default is False:
                raise TokenInvalidError('no such request token.')
            return default

        if token.access:
            if default is False:
                raise NotRequestTokenError('not a request token.')
            return default

        return token

    def getAccessToken(self, token, default=False):
        token = self.get(token, default)
        if token is default:
            if default is False:
                raise TokenInvalidError('no such access token.')
            return default

        if not token.access:
            if default is False:
                raise NotAccessTokenError('not an access token.')
            return default

        # must be identified
        if not token.user:
            raise TokenInvalidError('token has no user')
        raw_keys = self._user_token_map.get(token.user, [])
        if token.key not in raw_keys:
            raise TokenInvalidError('user `%s` does not own this key' 
                % token.user)

        return token

    def getTokensForUser(self, user):
        raw_keys = self._user_token_map.get(user, [])
        result = [self.get(t) for t in raw_keys]
        return result

    def remove(self, token):
        if IToken.providedBy(token):
            token = token.key
        token = self._tokens.pop(token)
        self._del_user_map(token)
        return token

    def requestTokenVerify(self, consumer_key, token, verifier):
        """\
        Verify that the request results in a valid token by checking for
        validity of the consumer_key and verifier.
        """

        token = self.getRequestToken(token)
        return (token.consumer_key == consumer_key and 
                token.verifier == verifier and
                token.user is not None
                )

TokenManagerFactory = factory(TokenManager)


class Token(Persistent):

    zope.interface.implements(IToken)

    key = fieldproperty.FieldProperty(IToken['key'])
    secret = fieldproperty.FieldProperty(IToken['secret'])
    callback = fieldproperty.FieldProperty(IToken['callback'])
    verifier = fieldproperty.FieldProperty(IToken['verifier'])
    access = fieldproperty.FieldProperty(IToken['access'])

    user = fieldproperty.FieldProperty(IToken['user'])
    consumer_key = fieldproperty.FieldProperty(IToken['consumer_key'])
    timestamp = fieldproperty.FieldProperty(IToken['timestamp'])
    expiry = fieldproperty.FieldProperty(IToken['expiry'])

    def __init__(self, key, secret):
        assert not ((key is None) or (secret is None))
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        """
        Set the callback URI.
        """

        self.callback = callback

    def set_verifier(self, verifier=None):
        """
        Based on implementation from python-oauth2
        
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
        """
        Based on implementation from python-oauth2, with corrections.
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
