import urllib
import urlparse
from time import time
from random import randint
from sys import maxint
from cStringIO import StringIO

from oauthlib.oauth1 import Client
from oauthlib.common import Request

import zope.interface
from zope.annotation.interfaces import IAttributeAnnotatable

from Testing import ZopeTestCase as ztc
from Zope2.App import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
from Products.PloneTestCase.layer import onsetup
from Products.PloneTestCase.layer import onteardown

import z3c.form.testing

import pmr2.z3cform.tests.base
from pmr2.oauth.plugins.oauth import OAuthPlugin

@onsetup
def setup():
    import pmr2.oauth
    fiveconfigure.debug_mode = True
    zcml.load_config('configure.zcml', pmr2.oauth)
    zcml.load_config('tests.zcml', pmr2.oauth.tests)
    fiveconfigure.debug_mode = False
    ztc.installPackage('pmr2.oauth')

@onteardown
def teardown():
    pass

setup()
teardown()
ptc.setupPloneSite(products=('pmr2.oauth',))


class IOAuthTestLayer(zope.interface.Interface):
    """\
    Mock layer
    """


def escape(s):
    return urllib.quote(s.encode('utf-8'), safe='~')


class TestRequest(pmr2.z3cform.tests.base.TestRequest):

    zope.interface.implements(IOAuthTestLayer, IAttributeAnnotatable)

    def __init__(self, oauth_keys=None, url=None, method=None, *a, **kw):
        super(TestRequest, self).__init__(*a, **kw)
        if url:
            parts = url.split('/')
            self._app_server = '/'.join(parts[:3])
            self._app_names = parts[3:]

        url = self.getURL()
        self.other = {}
        # Actual classes look for this
        self.other['ACTUAL_URL'] = url
        # Some other way of accessing this...
        self._environ['ACTUAL_URL'] = url

        if oauth_keys:
            self._auth = self.to_header(oauth_keys)

        self.stdin = StringIO()
        if method:
            self.method = method

    def to_header(self, oauth_keys, realm=''):
        # copied from oauth2 (for now)
        oauth_params = ((k, v) for k, v in oauth_keys.items()
                            if k.startswith('oauth_'))
        stringy_params = ((k, escape(str(v))) for k, v in oauth_params)
        header_params = ('%s="%s"' % (k, v) for k, v in stringy_params)
        params_header = ', '.join(header_params)

        auth_header = 'OAuth realm="%s"' % realm
        if params_header:
            auth_header = "%s, %s" % (auth_header, params_header)

        return auth_header


def SignedTestRequest(form=None, consumer=None, token=None, method=None,
        url=None, callback=None, timestamp=None, verifier=None,
        signature_type='AUTH_HEADER', raw_body=None,
        *a, **kw):
    """\
    Creates a signed TestRequest
    """

    def safe_unicode(s):
        # I really really hate oauthlib's insistence on using unicode
        # on things that are really bytes.
        if isinstance(s, str):
            return unicode(s)

        return s

    if not consumer:
        raise ValueError('consumer must be provided to build a signed request')

    if form is None:
        form = {}

    result = TestRequest(form=form, url=url, method=method, *a, **kw)
    if raw_body:
        result.stdin.write(raw_body)

    url = url or result.getURL()
    url = safe_unicode(url)
    method = method and safe_unicode(method) or safe_unicode(result.method)
    timestamp = timestamp or unicode(int(time()))

    token_key = token and token.key
    token_secret = token and token.secret

    client = Client(
        safe_unicode(consumer.key),
        safe_unicode(consumer.secret),
        safe_unicode(token_key),
        safe_unicode(token_secret),
        safe_unicode(callback),
        verifier=safe_unicode(verifier),
        timestamp=timestamp,
        signature_type=signature_type,
    )

    if result.getHeader('Content-Type') == 'application/x-www-form-urlencoded':
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url_signed, headers, body = client.sign(url, method,
            body=raw_body, headers=headers)
    else:
        url_signed, headers, body = client.sign(url, method)

    # lazy not importing oauthlib tokens.
    if signature_type == 'AUTH_HEADER':
        result._auth = headers['Authorization']
        return result
    elif signature_type == 'QUERY':
        qs = urlparse.urlsplit(url_signed).query
        result = TestRequest(form=form, url=url, QUERY_STRING=qs, *a, **kw)
        if raw_body:
            result.stdin.write(raw_body)
        return result

def makeToken(qsstr):
    # quick and dirty, don't do this for real.
    d = urlparse.parse_qs(qsstr)
    t = {}
    t['key'] = d.get('oauth_token', ['']).pop()
    t['secret'] = d.get('oauth_token_secret', ['']).pop()
    return type('Token', (object,), t)
