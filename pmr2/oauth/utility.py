import os
import base64
import zope.interface

from pmr2.oauth.interfaces import IOAuthUtility


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


def random_string(length):
    """\
    Request a random string up to this length.

    This method attempts to use the OS provided random bytes 
    suitable for cryptographical use (see os.urandom), base64 
    encoded (see base64.urlsafe_b64encode).  Hence actual length
    will be divisible by 4.
    """

    actual = int(length / 4) * 3
    return base64.urlsafe_b64encode(os.urandom(actual))
