import zope.component
from zope.publisher.browser import BrowserPage

from zExceptions import BadRequest
from zExceptions import Forbidden

from pmr2.oauth.interfaces import *


class RequestTokenPage(BrowserPage):

    def __call__(self):
        o_request = zope.component.getAdapter(self.request, IRequest)

        if not o_request:
            raise BadRequest()

        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)

        consumer = cm.get(o_request['oauth_consumer_key'], None)
        if not consumer:
            raise BadRequest('Invalid consumer key')

        oauth = zope.component.getUtility(IOAuthUtility)
        try:
            params = oauth.verify_request(o_request, consumer, None)
        except oauth.Error:
            raise BadRequest('Could not verify OAuth request.')

        # create token

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        token = tm.generateRequestToken(consumer, o_request)

        # return token
        return token.to_string()
