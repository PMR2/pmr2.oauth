import os
import base64

import oauthlib.oauth1

import zope.interface
import zope.schema
from zope.app.component.hooks import getSite

from Products.CMFCore.utils import getToolByName

from pmr2.oauth.interfaces import TokenInvalidError, ICallbackManager
from pmr2.oauth.interfaces import IOAuthAdapter, INonceManager
from pmr2.oauth.interfaces import IConsumerManager, ITokenManager

from pmr2.oauth.schema import buildSchemaInterface

SAFE_ASCII_CHARS = set([chr(i) for i in xrange(32, 127)])


class SiteRequestOAuth1ServerAdapter(oauthlib.oauth1.Server):
    """
    Completing the implementation of the server as an adapter that
    unifies the authentication process.
    """

    zope.interface.implements(IOAuthAdapter)

    def __init__(self, site, request):
        self.consumerManager = zope.component.getMultiAdapter(
            (site, request), IConsumerManager)
        self.tokenManager = zope.component.getMultiAdapter(
            (site, request), ITokenManager)
        self.callbackManager = zope.component.getMultiAdapter(
            (site, request), ICallbackManager)
        # Optional at this point.
        self.nonceManager = zope.component.queryMultiAdapter(
            (site, request), INonceManager)

        self.access_key = None

        self.site = site
        self.request = request

        # All OAuth related terms are placed in the Authorization.
        # Using unicode because lol oauthlib's obsession with 
        # unicode_literals, which adds nothing but annoyance when the
        # protocol is fundamentally in bytes.

        self.uri = safe_unicode(extractRequestURL(request))
        self.http_method = safe_unicode(request.method)

        # These are the only headers that affect the signature for
        # an OAuth request.

        self.headers = {
            u'Content-type': safe_unicode(request.getHeader('Content-type')),
            u'Authorization': safe_unicode(request._auth),
        }

        request.stdin.seek(0)
        self.body = safe_unicode(request.stdin.read())

    # Local helpers.

    def __call__(self):
        result, request = self.verify_pas_request()
        if result:
            # Only set the access key if access was granted.
            self.client_key = request.client_key
            self.access_key = request.resource_owner_key
        # We only want a True or False value.
        return result

    def mark_request(self, oauth_request):
        """
        Mark the request object with a flag to give hints for the token
        management pages.
        """

        self.request._pmr2_oauth1_ = oauth_request

    def verify_pas_request(self):
        """
        Verify a standard request with all checks in order to not
        trigger a BadRequest or Forbidden error prematurely, which would
        prevent access to the RequestToken and AccessToken pages.
        """

        req_result = acc_result = result = None
        acc_request = req_request = request = None 

        try:
            req_result, req_request = self.verify_request_token_request()
        except ValueError:
            pass

        try:
            acc_result, acc_request = self.verify_access_token_request()
        except ValueError:
            pass

        try:
            result, request = self.verify_resource_request()
        except ValueError:
            if not (req_result or acc_result):
                raise

        if result is False:
            # Check to see if either one of those passed.  Return an
            # undefined result (as None) and whichever request object
            # that got generated.
            if req_result:
                self.mark_request(req_request)
                return None, req_request

            if acc_result:
                self.mark_request(acc_request)
                return None, acc_request

        return result, request

    def verify_resource_request(self):
        """
        For verification of requests for accessing resources.
        """

        return self.verify_request(
            require_resource_owner=True,
            require_verifier=False,
            require_callback=False,
        )

    def verify_request_token_request(self):
        """
        For verification of requests for getting RequestTokens.
        """

        return self.verify_request(
            require_resource_owner=False, 
            require_verifier=False,
            require_callback=True,
        )

    def verify_access_token_request(self):
        """
        For verification of requests for getting AccessTokens.
        """

        return self.verify_request(
            require_resource_owner=True, 
            require_verifier=True,
            require_callback=False,
        )

    # Overrides

    def verify_request(self, uri=None, http_method=None, body=None,
            headers=None, require_resource_owner=True, require_verifier=False,
            require_realm=False, required_realm=None, require_callback=False,
            *a, **kw):
        """
        Essentially a clone of the parent class, but the default 
        parameters will be from this class.
        """

        if uri is None:
            uri = self.uri
        if http_method is None:
            http_method = self.http_method
        if body is None:
            body = self.body
        if headers is None:
            headers = self.headers

        return super(SiteRequestOAuth1ServerAdapter, self).verify_request(
            uri, http_method, body, headers, 
            require_resource_owner, require_verifier, require_realm,
            required_realm)

    # Property overrides

    @property
    def enforce_ssl(self):
        # Since the reverse proxy does not provide any ssl and any 
        # secure traffic would not be reflected here.  However, this
        # value is used to verify whether to need the https be in the
        # signing URL, so there might be a need to provide a way to
        # configure this.
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
        return u''

    # Implementation

    def get_client_secret(self, client_key):
        consumer = self.consumerManager.getValidated(client_key)
        # Spend actual time failing.
        dummy = self.consumerManager.getValidated(
            self.consumerManager.DUMMY_KEY)

        if consumer:
            result = consumer.secret
        else:
            result = self.consumerManager.DUMMY_SECRET

        return unicode(result)

    @property
    def dummy_client(self):
        result = self.consumerManager.DUMMY_KEY
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
        result = token and token.key or self.tokenManager.DUMMY_KEY

        return unicode(result)

    @property
    def dummy_access_token(self):
        token = self.tokenManager.get(self.tokenManager.DUMMY_KEY)
        result = token and token.key or self.tokenManager.DUMMY_KEY

        return unicode(result)

    def get_rsa_key(self, client_key):
        # TODO figure out how to implement this.
        raise NotImplementedError

    def validate_client_key(self, client_key):
        # This will search through the table to acquire a failed dummy key
        dummy = self.consumerManager.get(self.consumerManager.DUMMY_KEY,
            self.consumerManager.makeDummy())
        consumer = self.consumerManager.getValidated(client_key, dummy)
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
        # Redirect URI will be external, verify that it is in the
        # same format as it was registered for the consumer.
        if redirect_uri is None:
            # Most requests will not have this defined.
            return True

        # Only the token request will have this
        consumer = self.consumerManager.getValidated(client_key)
        return self.callbackManager.validate(consumer, redirect_uri)

    def validate_requested_realm(self, client_key, realm):
        # Realms are not handled.
        return True

    def validate_realm(self, client_key, access_token, uri=None,
            required_realm=None):
        # Realms are not handled.
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

def safe_unicode(s):
    if isinstance(s, str):
        return unicode(s)
    return s
   
def getUserPortalTypes():
    site = getSite()
    portal_catalog = getToolByName(site, 'portal_catalog')
    plone_utils = getToolByName(site, 'plone_utils')
    portal_types = getToolByName(site, 'portal_types')
    all_used_types = portal_catalog.uniqueValuesFor('portal_type');
    all_friendly_types = plone_utils.getUserFriendlyTypes(all_used_types)
    # XXX assumption, should use portal_types.getTypeInfo
    root = [('Plone Site', 'Plone Site')]  
    main = [(t, portal_types.getTypeInfo(t).title) for t in all_friendly_types]
    return root + sorted(main, lambda x, y: cmp(x[1], y[1]))

def schemaFactory(**kw):
    title = unicode(kw.pop('title'))
    required = kw.pop('required')
    return zope.schema.List(title=title, required=required,
        value_type=zope.schema.ASCIILine())

def buildContentTypeScopeProfileInterface():
    types = getUserPortalTypes()
    return buildSchemaInterface(types, schemaFactory, sort=False)
