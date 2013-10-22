import os
import base64
from urllib import quote_plus

import oauthlib.oauth1
from oauthlib.common import urldecode

import zope.interface
import zope.schema
from zope.component.hooks import getSite

from Products.CMFCore.utils import getToolByName

from pmr2.oauth.interfaces import OAuth1Error
from pmr2.oauth.interfaces import TokenInvalidError, ICallbackManager
from pmr2.oauth.interfaces import IOAuthRequestValidatorAdapter, INonceManager
from pmr2.oauth.interfaces import IConsumerManager, ITokenManager
from pmr2.oauth.interfaces import IScopeManager

from pmr2.oauth.schema import buildSchemaInterface, CTSMMappingList

SAFE_ASCII_CHARS = set([chr(i) for i in xrange(32, 127)])


class SiteRequestValidatorAdapter(oauthlib.oauth1.RequestValidator):
    """
    Completing the implementation of the server as an adapter that
    unifies the authentication process.
    """

    zope.interface.implements(IOAuthRequestValidatorAdapter)

    def __init__(self, site, request):
        # consider adapting self rather than site for these managers?
        # this might make it easier to provide a whole suite of managers
        # for a given validator.
        self.consumerManager = zope.component.getMultiAdapter(
            (site, request), IConsumerManager)
        self.tokenManager = zope.component.getMultiAdapter(
            (site, request), ITokenManager)
        self.callbackManager = zope.component.getMultiAdapter(
            (site, request), ICallbackManager)

        # Really should not be optional, but this is only used within
        # the ``invalidate_request_token`` method
        self.scopeManager = zope.component.queryMultiAdapter(
            (site, request), IScopeManager)

        # Optional at this point.
        self.nonceManager = zope.component.queryMultiAdapter(
            (site, request), INonceManager)

        self.access_key = None

        self.site = site
        self.request = request

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

    def mark_request(self, oauth_request):
        """
        Mark the request object with a flag to give hints for the token
        management pages.
        """

        self.request._pmr2_oauth1_ = oauth_request

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

    @property
    def nonce_length(self):
        return 8, 64

    # Dummies to ensure near constant time validations.

    @property
    def dummy_client(self):
        result = self.consumerManager.DUMMY_KEY
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

    # Implementation

    def get_client_secret(self, client_key, request):
        consumer = self.consumerManager.getValidated(client_key)
        # Spend actual time failing.
        dummy = self.consumerManager.getValidated(
            self.consumerManager.DUMMY_KEY)

        if consumer:
            result = consumer.secret
        else:
            result = self.consumerManager.DUMMY_SECRET

        return unicode(result)

    def get_request_token_secret(self, client_key, request_token, request):
        token = self.tokenManager.getRequestToken(request_token, None)
        if token and token.consumer_key == client_key:
            result = token.secret
        else:
            result = self.tokenManager.DUMMY_SECRET

        return unicode(result)

    def get_access_token_secret(self, client_key, access_token, request):
        token = self.tokenManager.getAccessToken(access_token, None)
        if token and token.consumer_key == client_key:
            result = token.secret
        else:
            result = self.tokenManager.DUMMY_SECRET

        return unicode(result)

    def get_default_realms(self, client_key, request):
        return []

    def get_realms(self, client_key, request):
        return []

    def get_redirect_uri(self, token, request):
        # We have our own AuthorizationEndpoint that do not use this.
        raise NotImplementedError

    def get_rsa_key(self, client_key, request):
        # TODO figure out how to implement this.
        raise NotImplementedError

    def invalidate_request_token(self, client_key, request_token, request):
        # purge the scope
        if self.scopeManager:
            scope = self.scopeManager.popScope(request_token, None)
        # and then the token
        token = self.tokenManager.getRequestToken(request_token, None)
        if token:
            self.tokenManager.remove(token)

    def validate_client_key(self, client_key, request):
        # This will search through the table to acquire a failed dummy key
        dummy = self.consumerManager.get(self.consumerManager.DUMMY_KEY,
            self.consumerManager.makeDummy())
        consumer = self.consumerManager.getValidated(client_key, dummy)
        return consumer.validate() and consumer != dummy

    def validate_request_token(self, client_key, request_token, request):
        # XXX request_token <- token in parent
        token = self.tokenManager.getRequestToken(request_token, 
            self.dummy_request_token)
        return (token != self.dummy_request_token and 
            token.consumer_key == client_key)

    def validate_access_token(self, client_key, access_token, request):
        token = self.tokenManager.getAccessToken(access_token, 
            self.dummy_access_token)
        return (token != self.dummy_access_token and 
            token.consumer_key == client_key)

    def validate_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request, request_token=None, access_token=None):
        if self.nonceManager:
            # TODO figure out the parameters.
            return self.nonceManager.validate(timestamp, nonce)
        # Just let this one go...
        return True

    def validate_redirect_uri(self, client_key, redirect_uri, request):
        # Redirect URI will be external, verify that it is in the
        # same format as it was registered for the consumer.
        if redirect_uri is None:
            # Most requests will not have this defined.
            return True

        # Only the token request will have this
        consumer = self.consumerManager.getValidated(client_key)
        return self.callbackManager.validate(consumer, redirect_uri)

    def validate_requested_realms(self, client_key, realms, request):
        # Realms are not handled.
        return True

    def validate_realms(self, client_key, token, request, uri=None,
            realms=None):
        # Realms are not handled.
        return True

    def validate_verifier(self, client_key, request_token, verifier, request):
        try:
            return self.tokenManager.requestTokenVerify(
                client_key, request_token, verifier)
        except TokenInvalidError:
            return False

    def save_access_token(self, token, request):
        # generated tokens automatically saved.
        return

    def save_request_token(self, token, request):
        # generated tokens automatically saved.
        return

    def save_verifier(self, token, verifier, request):
        # generated verifier automatically saved.
        return


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
            # XXX this is _seriously_ a pita.  For some reason in some
            # circumstances we are not getting back the original encoded
            # values that we used to sign the request.  This rectifies
            # that.
            try:
                urldecode(query_string)
            except ValueError:
                query_string = quote_plus(query_string, safe='=&;%+~')
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
    return CTSMMappingList(title=title, required=required,
        value_type=zope.schema.ASCIILine())

def buildContentTypeScopeProfileInterface():
    types = getUserPortalTypes()
    return buildSchemaInterface(types, schemaFactory, sort=False)
