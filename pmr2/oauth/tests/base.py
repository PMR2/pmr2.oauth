from Testing import ZopeTestCase as ztc
from Zope2.App import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
from Products.PloneTestCase.layer import onsetup
from Products.PloneTestCase.layer import onteardown

import zope.publisher.browser
import oauth2 as oauth

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
#ptc.setupPloneSite(products=('pmr2.oauth',))
ptc.setupPloneSite(products=())


class TestRequest(zope.publisher.browser.TestRequest):

    def __init__(self, oauth_keys=None, *a, **kw):
        super(TestRequest, self).__init__(*a, **kw)
        if oauth_keys:
            req = oauth.Request("GET", self.getURL(), oauth_keys)
            headers = req.to_header()
            self._auth = headers['Authorization']


signature_method = oauth.SignatureMethod_HMAC_SHA1()

def SignedTestRequest(form=None, oauth_keys=None, consumer=None, token=None,
        *a, **kw):
    """\
    Creates a signed TestRequest
    """

    if not consumer:
        raise ValueError('Consumer must be provided')

    if form is None:
        form = {}

    result = TestRequest(form=form, *a, **kw)
    url = result.getURL()  # may want to make this an argument
    req = oauth.Request.from_consumer_and_token(
        consumer, token, http_url=url, parameters=oauth_keys)
    req.update(form)
    req.sign_request(signature_method, consumer, token)
    headers = req.to_header()
    result._auth = headers['Authorization']
    return result
