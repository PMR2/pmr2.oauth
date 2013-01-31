import urllib

import zope.component
import zope.interface
from zope.app.component.hooks import getSite
from zope.publisher.browser import BrowserPage
from zope.publisher.interfaces import NotFound

from zExceptions import BadRequest
from zExceptions import Forbidden
from zExceptions import Unauthorized

from z3c.form import button

from Products.CMFCore.utils import getToolByName

from pmr2.z3cform import form

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import *
from pmr2.oauth.browser.template import ViewPageTemplateFile
from pmr2.oauth.browser.template import path

_marker = object()


class BaseTokenPage(BrowserPage):

    # token to return
    token = None

    def _verifyToken(self, oauth):
        # Return the correct OAuth method for the respective token 
        # request page.
        raise NotImplementedError()

    def getOAuth1(self):
        if not hasattr(self.request, '_pmr2_oauth1_'):
            site = getSite()
            oauthAdapter = zope.component.getMultiAdapter((site, self.request),
                IOAuthAdapter)
            try:
                result, oauth1 = self._verifyToken(oauthAdapter)
            except ValueError:
                raise BadRequest()
            if not result:
                raise Forbidden()
            #self.request._pmr2_oauth1_ = oauth1
            return oauth1
        else:
            # Prepared by the run at the plugin.
            return self.request._pmr2_oauth1_

    def update(self):
        # Considering modifying to call something like create and store
        # token and store scope.
        raise NotImplementedError()

    def render(self):
        token = self.token
        data = {
            'oauth_token': token.key,
            'oauth_token_secret': token.secret,
        }
        if token.callback is not None:
            data['oauth_callback_confirmed'] = 'true'
        return urllib.urlencode(data)

    def __call__(self):
        self.update()
        return self.render()


class RequestTokenPage(BaseTokenPage):

    def _verifyToken(self, oauth):
        # See parent class
        return oauth.verify_request_token_request()

    def update(self):
        oauth1 = self.getOAuth1()

        # NOTE Currently it is impossible to disable callback validation
        # in oauthlib, so verify that callback is really provided.
        if not oauth1.callback_uri:
            raise BadRequest()

        # This is an 8-bit protocol, so we cast the oauthlib request
        # parameters into something we would expect from the http spec.
        # Yes, I am aware something about unicode literals in Python 3,
        # but this transition period is just a giant pita.
        # If these kind of casting dies in a fire I don't really care
        # because these should all be ascii for simplicity.
        consumer_key = str(oauth1.client_key)
        callback = str(oauth1.callback_uri)

        # create request token
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        self.token = tm.generateRequestToken(consumer_key, callback)

        # store the scope.
        scope = self.request.get('scope', None)
        key = self.token.key
        sm = zope.component.getMultiAdapter((self.context, self.request),
            IScopeManager)
        if not sm.requestScope(key, scope):
            raise Forbidden()


class GetAccessTokenPage(BaseTokenPage):

    def _verifyToken(self, oauth):
        # See parent class
        return oauth.verify_access_token_request()

    def update(self):
        oauth1 = self.getOAuth1()

        consumer_key = str(oauth1.client_key)
        token_key = str(oauth1.resource_owner_key)
        verifier = str(oauth1.verifier)

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        self.token = tm.generateAccessToken(consumer_key, token_key)

        # move the scope stored into the access token.
        sm = zope.component.getMultiAdapter((self.context, self.request),
            IScopeManager)

        scope = sm.popScope(token_key, _marker)
        if scope == _marker:
            # could not find the scope that was stored.
            raise Forbidden()

        key = self.token.key
        sm.setAccessScope(key, scope)


class AuthorizeTokenForm(form.PostForm, BaseTokenPage):

    ignoreContext = True
    invalidTokenMessage = _(u'Invalid Token.')
    invalidConsumerMessage = _(
        u'Consumer associated with this key is invalid.')
    deniedMessage = _(
        u'Token has been denied.')
    callbackInvalidMessage = _(
        u'Callback is not approved for the client.  Aborted.')
    token = None
    consumer = None
    description = ''
    verifier = ''
    statusTemplate = ViewPageTemplateFile(path('authorize_status.pt'))
    verifierTemplate = ViewPageTemplateFile(path('authorize_verifier.pt'))
    template = ViewPageTemplateFile(path('authorize_question.pt'))
    _errors = False

    def _checkConsumer(self, key):
        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)

        consumer = cm.getValidated(key)
        if not consumer:
            raise ConsumerInvalidError('invalid consumer')
        return consumer

    def _checkToken(self, key):
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)

        token = tm.get(key)
        if not token:
            raise TokenInvalidError('invalid token')
        return token

    def _update(self):
        token_key = self.request.form.get('oauth_token', None)
        token = self._checkToken(token_key)
        consumer = self._checkConsumer(token.consumer_key)
        self.token = token
        self.consumer = consumer

        sm = zope.component.getMultiAdapter((self.context, self.request),
            IScopeManager)
        view = zope.component.getMultiAdapter((sm, self.request),
            name='token_scope_view')
        view.omit_index = True
        try:
            self.scope = view()
        except NotFound:
            raise TokenInvalidError()

    def update(self):
        """\
        We do need an actual user, not sure which permission level will
        get me to do what I want in the zcml, hence we will need to
        manually check.
        """

        self.request['disable_border'] = True
        mt = getToolByName(self.context, 'portal_membership')
        if mt.isAnonymousUser():
            # should trigger a redirect to some login mechanism.
            raise Unauthorized()

        try:
            self._update()
        except TokenInvalidError, e:
            self._errors = self.invalidTokenMessage
        except ConsumerInvalidError, e:
            self._errors = self.invalidConsumerMessage

        if self._errors:
            self.status = self._errors
            self._errors = True

        return super(AuthorizeTokenForm, self).update() 

    def render(self):
        if self._errors:
            return self.statusTemplate()
        if self.verifier:
            return self.verifierTemplate()
        return super(AuthorizeTokenForm, self).render()

    def callback(self, verifier):
        if self.token.callback == 'oob':
            # Assign the verifier to this form to render for resource
            # owner's usage.
            self.verifier = verifier
            return True

        callback_url = self.token.get_callback_url()
        cbm = zope.component.getMultiAdapter((self.context, self.request),
            ICallbackManager)
        result = cbm.validate(self.consumer, callback_url)

        if result:
            # XXX what to do with the trusted parameter introduced in
            # between zope.publisher.http.HTTPRequest vs.
            # ZPublisher.HTTPResponse.HTTPResponse, as the latter does
            # not deal with that, and if this is in repoze, without
            # that redirection will not work.
            self.request.response.redirect(callback_url)
        else:
            # Abort; somehow the request token was approved prematurely
            # despite callback mismatch; perhaps the conditions have
            # changed?
            self._errors = True
            self.status = self.callbackInvalidMessage

        return result

    @button.buttonAndHandler(_('Grant access'), name='approve')
    def handleApprove(self, action):
        """\
        User approves this token.
        
        Redirect user to the callback URL to give the provider the OAuth
        Verifier key.
        """

        if self._errors or not self.token:
            return

        data, errors = self.extractData()

        mt = getToolByName(self.context, 'portal_membership')
        user = mt.getAuthenticatedMember().id

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        if self.callback(self.token.verifier):
            tm.claimRequestToken(self.token, user)

    @button.buttonAndHandler(_('Deny access'), name='deny')
    def handleDeny(self, action):
        """\
        User denies this token
        """

        if self._errors or not self.token:
            return

        data, errors = self.extractData()

        token_key = self.request.form.get('oauth_token', None)
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        tm.remove(token_key)
        sm = zope.component.getMultiAdapter((self.context, self.request),
            IScopeManager)
        sm.popScope(token_key, None)
        # we will let the client deal with rejection, if callback is
        # valid.
        self.callback(self.token.verifier)
        # if that wasn't valid, this is really the failure message.
        self.status = self.deniedMessage
        self._errors = True
