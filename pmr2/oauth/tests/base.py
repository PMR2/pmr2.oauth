from Testing import ZopeTestCase as ztc
from Zope2.App import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
from Products.PloneTestCase.layer import onsetup
from Products.PloneTestCase.layer import onteardown

import zope.publisher.browser
import oauth2

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
            req = oauth2.Request("GET", self.getURL(), oauth_keys)
            headers = req.to_header()
            self._auth = headers['Authorization']
