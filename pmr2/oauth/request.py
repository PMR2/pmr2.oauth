import zope.interface
from zope.publisher.interfaces.browser import IBrowserRequest

import oauth2
from pmr2.oauth import interfaces


class Request(oauth2.Request):
    zope.interface.implements(interfaces.IRequest)


def BrowserRequestAdapter(request):
    return oauth2.Request.from_request(
        request.method,
        request.getURL(),
        # ZPublisher.HTTPRequest by default has the raw Authentication
        # header as a string separated out in request._auth.
        headers={'Authorization': request._auth},
        parameters=request.form,
    )
