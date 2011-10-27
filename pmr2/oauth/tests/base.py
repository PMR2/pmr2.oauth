from time import time
from random import randint
from sys import maxint
import zope.interface
from zope.annotation.interfaces import IAttributeAnnotatable

from Testing import ZopeTestCase as ztc
from plone.session.tests.sessioncase import PloneSessionTestCase
from Zope2.App import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
from Products.PloneTestCase.layer import onsetup
from Products.PloneTestCase.layer import onteardown

import z3c.form.testing
import oauth2 as oauth
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


class OAuthTestCase(PloneSessionTestCase):

    def afterSetUp(self):
        PloneSessionTestCase.afterSetUp(self)
        self.app.folder = self.folder

        if self.folder.pas.hasObject("oauth"):
            self.app.folder.pas._delObject("oauth")

        self.app.folder.pas._setObject("oauth", OAuthPlugin("oauth"))


class IOAuthTestLayer(zope.interface.Interface):
    """\
    Mock layer
    """


class TestRequest(z3c.form.testing.TestRequest):

    zope.interface.implements(IOAuthTestLayer, IAttributeAnnotatable)

    def __setitem__(self, key, value):
        self.form[key] = value

    def __getitem__(self, key):
        try:
            return super(TestRequest, self).__getitem__(key)
        except KeyError:
            return self.form[key]

    def __init__(self, oauth_keys=None, url=None, *a, **kw):
        super(TestRequest, self).__init__(*a, **kw)
        url = url or self.getURL()
        self._environ['ACTUAL_URL'] = url
        if oauth_keys:
            req = oauth.Request("GET", url, oauth_keys)
            headers = req.to_header()
            self._auth = headers['Authorization']


signature_method = oauth.SignatureMethod_HMAC_SHA1()

def SignedTestRequest(form=None, oauth_keys=None, consumer=None, token=None,
        url=None, *a, **kw):
    """\
    Creates a signed TestRequest
    """

    if not consumer:
        raise ValueError('consumer must be provided to build a signed request')

    if form is None:
        form = {}

    nonce = str(randint(0, maxint))
    timestamp = str(int(time()))
    default_oauth_keys = {
        'oauth_version': "1.0",
        'oauth_nonce': nonce,
        'oauth_timestamp': timestamp,
    }

    if oauth_keys is None:
        oauth_keys = default_oauth_keys
    else:
        default_oauth_keys.update(oauth_keys)
        oauth_keys = default_oauth_keys

    result = TestRequest(form=form, *a, **kw)
    url = url or result.getURL()
    req = oauth.Request.from_consumer_and_token(
        consumer, token, http_url=url, parameters=oauth_keys)
    req.update(form)
    req.sign_request(signature_method, consumer, token)
    headers = req.to_header()
    result._auth = headers['Authorization']
    return result
