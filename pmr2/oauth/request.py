import zope.interface

import oauth2 as oauth
from pmr2.oauth import interfaces


class Request(oauth.Request):
    zope.interface.implements(interfaces.IRequest)


def BrowserRequestAdapter(request):
    auth = ''
    if request._auth:
        auth = request._auth

    result = oauth.Request.from_request(
        request.method,
        request.getURL(),
        # ZPublisher.HTTPRequest by default has the raw Authentication
        # header as a string separated out in request._auth.
        headers={'Authorization': auth},
        parameters=request.form,
    )
    if result:
        return result

    # I don't know WHY would a class method constructor return None
    # in this case...

    return oauth.Request(request.method, request.getURL())
