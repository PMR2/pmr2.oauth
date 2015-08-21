import zope.component

from zope.component.hooks import getSite
from oauthlib.oauth1.rfc5849.endpoints import base
from oauthlib.oauth1.rfc5849.errors import OAuth1Error
from oauthlib.oauth1 import ResourceEndpoint

from pmr2.oauth.interfaces import IOAuthRequestValidatorAdapter
from pmr2.oauth.utility import safe_unicode, extractRequestURL


class BaseEndpoint(base.BaseEndpoint):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def request_validator(self):
        site = getSite()
        return zope.component.getMultiAdapter((site, self.request),
            IOAuthRequestValidatorAdapter)

    @property
    def token_generator(self):
        raise NotImplementedError('Unused in this implementation')

    def _create_request(self, uri=None, http_method=None, body=None,
            headers=None):

        if uri is None:
            uri = safe_unicode(extractRequestURL(self.request))
        if http_method is None:
            http_method = safe_unicode(self.request.method)

        if headers is None:
            # These are the only headers that affect the signature for
            # an OAuth request.
            headers = {
                u'Content-Type':
                    safe_unicode(self.request.getHeader('Content-type', '')),
            }
            if self.request._auth:
                headers[u'Authorization'] = safe_unicode(self.request._auth)

        if body is None:
            self.request.stdin.seek(0)
            body = safe_unicode(self.request.stdin.read())

        return base.BaseEndpoint._create_request(self,
            uri, http_method, body, headers)


class ResourceEndpointValidator(BaseEndpoint, ResourceEndpoint):
    """
    Only provide the core validation, built on top of the magic we have.
    """

    def check_request(self):
        """
        Raise exception on errors involving with the structure of the
        request.
        """

        request = self._create_request()
        self._check_transport_security(request)
        self._check_mandatory_parameters(request)

        if not request.resource_owner_key:
            # assume not a request.
            return False

        if not self.request_validator.check_access_token(
                request.resource_owner_key):
            raise OAuth1Error

        if not self.request_validator.validate_timestamp_and_nonce(
                request.client_key, request.timestamp, request.nonce, request,
                access_token=request.resource_owner_key):
            raise OAuth1Error

        return True

