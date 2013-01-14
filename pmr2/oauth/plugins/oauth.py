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

        # Please see _validateScope
        scope = self._validateScope(site, request,
            verifier.client_key, verifier.access_key)
        if scope is False:
            raise Forbidden('invalid scope')

        if scope is None:
            # No scope manager?
            return {}

        mappings = {}
        token = verifier.tokenManager.getAccessToken(verifier.access_key)
        mappings['userid'] = token.user
        return mappings

    def _validateScope(self, site, request, client_key, access_key):
        # This should really be done outside of here by a customized
        # SecurityManager/Policy, which PAS will invoke some time after
        # this plugin is called.  However I have no time to figure out 
        # how or where to start, so a short-circuit process is done here 
        # for now.
        
        pas = self._getPAS()
        accessed, container, name, value = pas._getObjectContext(
            request.PUBLISHED, request)

        scopeManager = zope.component.queryMultiAdapter(
            (site, request), IScopeManager)
        if not scopeManager:
            # This normally shouldn't happen...
            return
        
        scopeValidity = scopeManager.validate(request, client_key, access_key, 
            accessed=accessed,
            container=container,
            name=name,
            value=value,
        )

        return scopeValidity

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
