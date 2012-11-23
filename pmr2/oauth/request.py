import zope.interface

import oauth2 as oauth
from pmr2.oauth import interfaces


class Request(oauth.Request):
    zope.interface.implements(interfaces.IRequest)


def BrowserRequestAdapter(request):
    auth = ''
    if request._auth:
        auth = request._auth

    if 'ACTUAL_URL' in request.other:
        # The actual requested URL from the user, not internal one
        url = request.other['ACTUAL_URL']
    else:
        # For whatever reason that is not found, fall back to this, even
        # though this might end up failing because it may not match up
        # with the one the consumer used to generate the checksum with.
        url = request.getURL()

    result = None
    try:
        # ZPublisher.HTTPRequest by default has the raw Authentication
        # header as a string separated out in request._auth.
        headers = {'Authorization': auth}

        # For some reason request.form includes the data as a key.  We
        # just omit that if that's the case.
        parameters = None
        if request.method == 'GET' or (request.method == 'POST' and
                request.getHeader('Content-Type') == 
                'application/x-www-form-urlencoded'):
            parameters = request.form

        result = oauth.Request.from_request(
            request.method,
            url,
            headers=headers,
            parameters=parameters,
        )

    except oauth.Error:
        # Argh.  Its constructor throws exception when bad user input
        # shows up?  Just return a standard request...
        result = oauth.Request(request.method, url)

    if result is None:
        # I don't know WHY would a class method constructor return None
        # in this case...
        result = oauth.Request(request.method, url)

    # disable feature from an outdated spec, which is the calculation
    # and inclusion of the oauth_body_hash
    result.is_form_encoded = True
    return result
