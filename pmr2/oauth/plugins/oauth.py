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

import logging

import oauth2 as oauth
from pmr2.oauth.interfaces import *


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

    def _getConsumer(self, site, request, o_request):
        consumerManager = zope.component.getMultiAdapter(
            (site, request), IConsumerManager)
        consumer_key = o_request.get('oauth_consumer_key')
        return consumerManager.get(consumer_key)

    def _checkScope(self, site, request, token):
        scopeManager = zope.component.queryMultiAdapter(
            (site, request), IScopeManager, name=token.scope_id)
        #if not scopeManager:
        #    # Assume a failed scope check.
        #    return False
        return scopeManager.validate(request, token)

    def extractOAuthCredentials(self, request):
        """\
        This method extracts the OAuth credentials from the request.
        """

        site = getSite()
        o_request = zope.component.getAdapter(request, IRequest)

        token_key = o_request.get('oauth_token')
        if not token_key:
            # This is likely a new request for a request token
            return {}

        tokenManager = zope.component.getMultiAdapter(
            (site, request), ITokenManager)

        try:
            token = tokenManager.getAccess(token_key)
        except NotAccessTokenError:
            # This is likely a request for an access token using this
            # request token.
            return {}
        except TokenInvalidError:
            raise Forbidden('invalid token')

        # consumer
        consumer = self._getConsumer(site, request, o_request)

        if consumer is None or not consumer.key == token.consumer_key:
            raise Forbidden('invalid consumer key')

        # verify token signature
        utility = zope.component.getUtility(IOAuthUtility)
        try:
            params = utility.verify_request(o_request, consumer, token)
        except oauth.Error, e:
            raise BadRequest(e.message)

        # lastly check whether request fits within the scope this token
        # is permitted to access.
        scope = self._checkScope(site, request, token)
        if not scope:
            raise Forbidden('invalid scope')

        result = {}
        fragment = 'oauth_'
        for k, v in o_request.iteritems():
            # as this is passed as keywords into other functions in PAS,
            # keys need to be strings
            key = k.encode('utf8')
            if key.startswith(fragment):
                result[key] = v

        result['userid'] = token.user
        return result

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
