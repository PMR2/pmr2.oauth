import oauth2
import zope.interface

from pmr2.oauth.interfaces import IOAuthUtility


class OAuthUtility(object):
    """
    The OAuth utility
    """

    zope.interface.implements(IOAuthUtility)

    def __init__(self):
        self.server = oauth2.Server()
        self.server.add_signature_method(oauth2.SignatureMethod_HMAC_SHA1())
        self.server.add_signature_method(oauth2.SignatureMethod_PLAINTEXT())

    def verify_request(self, request, consumer, token):
        return self.server.verify_request(request, consumer, token)
