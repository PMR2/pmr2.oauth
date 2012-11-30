import traceback
import logging

import zope.component
from zope.app.component.hooks import getSite

from AccessControl.SecurityInfo import ClassSecurityInfo
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.interfaces.plugins \
                import IAuthenticationPlugin, IExtractionPlugin

from zExceptions import Forbidden
from zExceptions import BadRequest

from pmr2.oauth.interfaces import IOAuthPlugin, IOAuthAdapter, IScopeManager


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
    zope.interface.implements(IOAuthPlugin)

    def __init__(self, id, title=None):
        self._setId(id)
        self.title = title

    # IExtractionPlugin implementation
    def extractCredentials(self, request):
        """\
        This method performs the PAS credential extraction.

        Consumer sends in credentials, which gets extracted.

        If the credential had been authenticated, return the login id,
        otherwise empty mapping.
        """

        if not (request._auth and request._auth.startswith('OAuth ')):
            # Skip all not OAuth related.
            return {}

        site = getSite()
        verifier = zope.component.getMultiAdapter(
            (site, request), IOAuthAdapter)

        try:
            result = verifier()
        except ValueError:
            raise BadRequest('bad oauth request')

        if result is None:
            # Valid request, but yielded no access key that will allow
            # this plugin to return a credential.
            return {}

        if result is False:
            raise Forbidden('authorization failed')

        scopeManager = zope.component.queryMultiAdapter(
            (site, request), IScopeManager)
        context = None
        if (scopeManager is None or not scopeManager.validate(
                context, verifier.client_key, verifier.access_key)):
            raise Forbidden('invalid scope')

        mappings = {}
        token = verifier.tokenManager.getAccessToken(verifier.access_key)
        mappings['userid'] = token.user
        return mappings

    # IAuthenticationPlugin implementation
    def authenticateCredentials(self, credentials):
        """\
        Authenticate the generated credentials by above.
        """

        if not credentials.get('extractor', None) == 'oauth':
            return None

        userid = credentials['userid']
        pas = self._getPAS()
        info = pas._verifyUser(pas.plugins, user_id=userid)
        if info is None:
            return None  # should we raise Forbidden instead?

        return (info['id'], info['login'])

classImplements(OAuthPlugin,
                IExtractionPlugin,
                IAuthenticationPlugin)
