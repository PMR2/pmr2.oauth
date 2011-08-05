from Acquisition import aq_parent
from AccessControl.SecurityInfo import ClassSecurityInfo
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.interfaces.plugins \
                import IAuthenticationPlugin, IExtractionPlugin
from zExceptions import Redirect
import transaction
import logging

manage_addOAuthPlugin = PageTemplateFile("../www/oauthAdd", globals(), 
                __name__="manage_addOAuthPlugin")

logger = logging.getLogger("PluggableAuthService")

def addOAuthPlugin(self, id, title='', REQUEST=None):
    """Add an OAuth plugin to a Pluggable Authentication Service.
    """
    p = OAuthPlugin(id, title)
    self._setObject(p.getId(), p)

    if REQUEST is not None:
        REQUEST["RESPONSE"].redirect("%s/manage_workspace"
                "?manage_tabs_message=OAuth+plugin+added." %
                self.absolute_url())


class OAuthPlugin(BasePlugin):
    """OAuth authentication plugin.
    """

    # to implement IExtractionPlugin, IAuthenticationPlugin
    meta_type = "OAuth plugin"
    security = ClassSecurityInfo()

    def __init__(self, id, title=None):
        self._setId(id)
        self.title = title
        # init storage too

    def getConsumer(self):
        pass

    def extractOAuthCredentials(self, request):
        """\
        This method extracts the OAuth credentials from the request.
        """

        result = {}
        fragment = 'oauth_'
        for k, v in request.form.iteritems():
            if k.startswith(fragment):
                result[k] = v
        return result

    def extractCredentials(self, request):
        """\
        This method performs the PAS credential extraction.

        Consumer sends in credentials, which gets extracted.

        If the credential had been authenticated, return the login id,
        otherwise empty mapping.
        """

        mappings = self.extractOAuthCredentials(request)
        #
        return {}

    # IAuthenticationPlugin implementation
    def authenticateCredentials(self, credentials):
        pass


classImplements(OAuthPlugin,
                IExtractionPlugin,
                IAuthenticationPlugin)
