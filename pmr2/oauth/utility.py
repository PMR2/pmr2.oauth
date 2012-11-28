import os
import base64

import oauthlib.oauth1

import zope.interface
from zope.app.component.hooks import getSite

from pmr2.oauth.interfaces import TokenInvalidError
from pmr2.oauth.interfaces import IOAuthUtility, INonceManager
from pmr2.oauth.interfaces import IConsumerManager, ITokenManager


class OAuthUtility(object):
    """
    The OAuth utility
    """

    zope.interface.implements(IOAuthUtility)

    def __init__(self):
        pass

    def verify_request(self, request, consumer, token):
        """\
        Verify an OAuth request with the given consumer and token.
        """

        raise NotImplementedError

SAFE_ASCII_CHARS = set([chr(i) for i in xrange(32, 127)])

class Server(oauthlib.oauth1.Server):
    """
    Completing the implementation of the server.
    """

    def __init__(self, site, request):
        self.consumerManager = zope.component.getMultiAdapter(
            (site, request), IConsumerManager)
        self.tokenManager = zope.component.getMultiAdapter(
            (site, request), ITokenManager)
        # Optional at this point.
        self.nonceManager = zope.component.queryMultiAdapter(
            (site, request), INonceManager)

    # Overrides

    @property
    def enforce_ssl(self):
        # Since the reverse proxy does not provide any ssl and any 
        # secure traffic would not be reflected here.
        return False

    @property
    def safe_characters(self):
        return SAFE_ASCII_CHARS

    @property
    def client_key_length(self):
        return 8, 64

    @property
    def request_token_length(self):
        return 8, 64

    @property
    def access_token_length(self):
        return 8, 64

    # Not implemented but used

    @property
    def dummy_resource_owner(self):
        # This is not actually used.
        return ''

    # Implementation

    def get_client_secret(self, client_key):
        consumer = self.consumerManager.get(client_key)
        if consumer:
            result = consumer.secret
        else:
            # TODO confirm time spent failing to allow this shortcut.
            result = self.consumerManager.DUMMY_SECRET

        return unicode(result)

    @property
    def dummy_client(self):
        consumer = self.consumerManager.get(self.consumerManager.DUMMY_KEY)
        result = consumer.key

        return unicode(result)

    def get_request_token_secret(self, client_key, request_token):
        token = self.tokenManager.getRequestToken(request_token, None)
        if token and token.consumer_key == client_key:
            result = token.secret
        else:
            result = self.tokenManager.DUMMY_SECRET

        return unicode(result)

    def get_access_token_secret(self, client_key, access_token):
        token = self.tokenManager.getAccessToken(access_token, None)
        if token and token.consumer_key == client_key:
            result = token.secret
        else:
            result = self.tokenManager.DUMMY_SECRET

        return unicode(result)

    @property
    def dummy_request_token(self):
        token = self.tokenManager.get(self.tokenManager.DUMMY_KEY)
        result = token.key

        return unicode(result)

    @property
    def dummy_access_token(self):
        token = self.tokenManager.get(self.tokenManager.DUMMY_KEY)
        result = token.key

        return unicode(result)

    def get_rsa_key(self, client_key):
        # TODO figure out how to implement this.
        raise NotImplementedError

    def validate_client_key(self, client_key):
        dummy = self.consumerManager.get(self.consumerManager.DUMMY_KEY)
        consumer = self.consumerManager.get(client_key, dummy)
        return consumer.validate() and consumer != dummy

    def validate_request_token(self, client_key, request_token):
        token = self.tokenManager.getRequestToken(request_token, 
            self.dummy_request_token)
        return (token != self.dummy_request_token and 
            token.consumer_key == client_key)

    def validate_access_token(self, client_key, access_token):
        token = self.tokenManager.getAccessToken(access_token, 
            self.dummy_access_token)
        return (token != self.dummy_access_token and 
            token.consumer_key == client_key)

    def validate_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        if self.nonceManager:
            # TODO figure out the parameters.
            return self.nonceManager.validate(timestamp, nonce)
        # Just let this one go...
        return True

    def validate_redirect_uri(self, client_key, redirect_uri):
        # Zope does this internally, deferr checking to that level.
        return True

    def validate_requested_realm(self, client_key, realm):
        # Realms are not currently used, but this could be used for
        # instantiating the correct scope manager.
        return True

    def validate_realm(self, client_key, access_token, uri=None,
            required_realm=None):
        # Realms are not used.
        return True

    def validate_verifier(self, client_key, request_token, verifier):
        try:
            return self.tokenManager.requestTokenVerify(
                client_key, request_token, verifier)
        except TokenInvalidError:
            return False


def random_string(length):
    """
    Request a random string up to this length.

    This method attempts to use the OS provided random bytes 
    suitable for cryptographical use (see os.urandom), base64 
    encoded (see base64.urlsafe_b64encode).  Hence actual length
    will be divisible by 4.
    """

    actual = int(length / 4) * 3
    return base64.urlsafe_b64encode(os.urandom(actual))


def extractRequestURL(request):
    # I am not sure why there isn't a thing that gets me the original
    # URI in the HTTP header and has to reconstruct all of this from
    # broken up pieces.

    actual_url = request.get('ACTUAL_URL', None)
    query_string = request.get('QUERY_STRING', None)
    
    if actual_url:
        result = actual_url
        if query_string:
            result += '?' + query_string
    else:
        # fallback.
        result = request.getURL()

    return result
