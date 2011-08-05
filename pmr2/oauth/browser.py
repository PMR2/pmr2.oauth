import zope.component
from zope.publisher.browser import BrowserPage

from zExceptions import BadRequest
from zExceptions import Forbidden

from pmr2.oauth.interfaces import IOAuthUtility
from pmr2.oauth.interfaces import IRequest
from pmr2.oauth.interfaces import IConsumerManager


class RequestToken(BrowserPage):

    def __call__(self):
        o_request = zope.component.getAdapter(request, IRequest)

        if not request:
            raise BadRequest()

        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)

        consumer = cm.get(o_request['oauth_consumer_key'], None)
        if not consumer:
            raise BadRequest('Invalid consumer key')

        oauth = zope.component.getUtility(IOAuthUtility)
        if not oauth.verify(consumer, o_request):
            raise BadRequest('Could not verify OAuth request.')

        # create token

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        token = tm.createToken(consumer, o_request)

        # return token
        return token.to_string()
