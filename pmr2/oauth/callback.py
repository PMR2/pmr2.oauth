import urlparse

import zope.component
import zope.interface

from pmr2.oauth.interfaces import ICallbackManager


class CallbackManager(object):
    """
    Default callback manager.
    """

    zope.interface.implements(ICallbackManager)

    def __init__(self, *a, **kw):
        pass

    def validate(self, consumer, callback):
        """
        Check whether callback is valid for this consumer.
        """

        if not consumer:
            return False

        domain = consumer.domain

        if callback == 'oob':
            # out of band is always valid.
            return True

        if not callback or not domain:
            return False

        parts = urlparse.urlparse(callback)
        scheme, netloc, path, params, query, fragment = parts[:6]

        # verify netloc against consumer's domain.

        if isinstance(domain, basestring) and domain.startswith('*.'):
            return netloc.endswith(domain[1:])

        return netloc == domain
