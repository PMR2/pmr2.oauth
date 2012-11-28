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

from pmr2.oauth.interfaces import *
from pmr2.oauth.utility import Server, extractRequestURL


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
        # init storage too

    def _checkScope(self, site, request, token):
        scopeManager = zope.component.queryMultiAdapter(
            (site, request), IScopeManager)
        #if not scopeManager:
        #    # Assume a failed scope check.
        #    return False
        return scopeManager.validate(request, token)

    def extractOAuthCredentials(self, request):
        """\
        This method extracts the OAuth credentials from the request.
        """

        if not request._auth or 'oauth_' not in request._auth:
            # Not signed with OAuth so no credentials can be found.
            return {}

        site = getSite()
        # TODO make this into an adapter?
        server = Server(site, request)
        uri = unicode(extractRequestURL(request))
        http_method = unicode(request.method)

        # We enforce all OAuth communications to using Authorization.
        headers = {
            'Authorization': unicode(request._auth),
        }

        # As this method is called due to it's place in the PAS, a full
        # authentication scheme will be called regardless.  So try the
        # main scheme that would yield a credentials.

        #bad_request = []
        auth_result = req_result = acc_result = None

        try:
            auth_result, o_request = server.verify_request(uri, 
                http_method=http_method, body=None, headers=headers, 
                require_resource_owner=True, require_verifier=False,
                )
        except ValueError:
            #bad_request.append('fail_main')
            pass

        # Failure.  Could still try to redeem this for the following
        # requests.

        try:
            # For acquiring request token
            req_result, req_request = server.verify_request(uri, 
                http_method=http_method, body=None, headers=headers, 
                require_resource_owner=False, require_verifier=False,
                )
        except ValueError:
            #bad_request.append('fail_requesttoken')
            pass

        try:
            # For exchanging of request token for access token
            acc_result, acc_request = server.verify_request(uri, 
                http_method=http_method, body=None, headers=headers, 
                require_resource_owner=True, require_verifier=True,
                )
        except ValueError:
            #bad_request.append('fail_getaccesstoken')
            pass

        # Return stuff here after all the checks have been done.

        if auth_result:
            # Got what is needd.
            return self._extractResultParams(site, server, request, o_request)

        if req_result or acc_result:
            # However these don't result in credentials, but at least
            # they are valid.
            return {}

        # Figure out how to fail this.
        results = (auth_result, req_result, acc_result)

        if False in results:
            # There is at least one successful failure.
            # should raise 401, but that falls back on cookie_auth.
            raise Forbidden('authorization failed.')

        # No successful failures.
        raise BadRequest('bad request')

    def _extractResultParams(self, site, server, request, o_request):
        """
        Lastly check whether request fits within the scope this token
        is permitted to access.  Done here because scope is not part
        of OAuth, also only sucessfully validated request can reach
        here so this does not need to be part of the delayed 
        validation.
        """

        token = server.tokenManager.getAccessToken(
            o_request.resource_owner_key)

        scope = self._checkScope(site, request, token)
        if not scope:
            raise Forbidden('invalid scope')

        signature_type, params, oauth_params = \
            server.get_signature_type_and_params(o_request)

        result_params = {}
        result_params.update(oauth_params)
        result_params['userid'] = token.user
        return result_params

    def extractCredentials(self, request):
        """\
        This method performs the PAS credential extraction.

        Consumer sends in credentials, which gets extracted.

        If the credential had been authenticated, return the login id,
        otherwise empty mapping.
        """

        if not (request._auth and request._auth.startswith('OAuth ')):
            return {}
        mappings = self.extractOAuthCredentials(request)
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
