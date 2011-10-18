import time
import urlparse
import oauth2 as oauth

from persistent import Persistent
from persistent.list import PersistentList
from BTrees.OOBTree import OOBTree

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable

import zope.interface
from zope.schema import fieldproperty

from pmr2.oauth.interfaces import IToken
from pmr2.oauth.interfaces import ITokenManager
from pmr2.oauth.interfaces import CallbackValueError
from pmr2.oauth.interfaces import TokenInvalidError
from pmr2.oauth.interfaces import NotAccessTokenError
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

    # expiry
    claim_timeout = 180
    
    def __init__(self):
        self._tokens = OOBTree()
        self._user_token_map = OOBTree()

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

    def _generateBaseToken(self, consumer, request):
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

        # This is our constrain.
        callback = request.get('oauth_callback')
        if callback is None:
            raise CallbackValueError(
                'callback must be specified or set to `oob`')

        token = self._generateBaseToken(consumer, request)
        token.set_callback(callback)
        token.set_verifier()

        # Assuming the scope stored in the token is a unicode string.
        # Let the TokenManagers deal with these values.
        token.scope = request.get('scope', u'')

        self.add(token)
        return token

    def generateAccessToken(self, consumer, request):
        if not self._tokenRequestVerify(request=request):
            raise TokenInvalidError('invalid token')
        old_key = request.get('oauth_token')
        old_token = self.get(old_key)
        
        token = self._generateBaseToken(consumer, request)
        token.access = True

        # copy over the vital attributes
        token.user = old_token.user
        token.scope = old_token.scope

        # Terminate old token to prevent reuse.
        self.remove(old_key)
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

    def getAccess(self, token, default=False):
        token = self.get(token, default)
        if token is default:
            if default is False:
                raise TokenInvalidError('no such access token.')
            return default

        if not token.access:
            raise NotAccessTokenError('not an access token.')

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

    def _tokenRequestVerify(self, request=None):
        """\
        Verify that the request results in a valid token.
        """

        token_key = request.get('oauth_token')
        token = self.get(token_key)
        if token is None:
            return False
        if int(time.time()) > token.expiry:
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
    expiry = fieldproperty.FieldProperty(IToken['expiry'])
    scope_id = fieldproperty.FieldProperty(IToken['scope_id'])
    scope = fieldproperty.FieldProperty(IToken['scope'])

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

