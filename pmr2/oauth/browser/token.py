import oauth2 as oauth

import zope.component
import zope.interface
from zope.publisher.browser import BrowserPage

from zExceptions import BadRequest
from zExceptions import Forbidden
from zExceptions import Unauthorized

from z3c.form import form
from z3c.form import button

from Products.CMFCore.utils import getToolByName

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import *
from pmr2.oauth.browser.template import ViewPageTemplateFile
from pmr2.oauth.browser.template import path
from pmr2.oauth.browser.form import Form


class BaseTokenPage(BrowserPage):

    # token to return
    token = None

    def _checkRequest(self, request):
        o_request = zope.component.getAdapter(request, IRequest)

        if not o_request:
            raise RequestInvalidError('missing oauth parameters')
        # XXX check and assemble a list of missing parameters.

        # Also verify the nonce here as this is common.
        self._checkNonce(o_request.get('oauth_nonce'))

        return o_request

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

    def _checkCallback(self, callback):
        m = zope.component.queryMultiAdapter((self.context, self.request),
            ICallbackManager)
        if m is None:
            # If this site does not implement any restriction on what
            # constitutes a valid callback, default is whitelist for
            # anything.  However, individual token managers can forcibly
            # enforce some hard values, such as not None or `oob`.
            return True
        return m.check(callback)

    def _checkNonce(self, nonce):
        m = zope.component.queryMultiAdapter((self.context, self.request),
            INonceManager)
        if m is None:
            # if we don't have a way to check nonce, we just have to
            # assume it is valid.
            return True
        return m.check(nonce)

    def _verifyOAuthRequest(self, o_request, consumer, token):
        # Check that this OAuth request is properly signed.
        utility = zope.component.getUtility(IOAuthUtility)
        try:
            params = utility.verify_request(o_request, consumer, token)
        except oauth.Error, e:
            raise RequestInvalidError(e.message)
        return True

    def update(self):
        raise NotImplemented

    def render(self):
        return self.token.to_string()

    def __call__(self):
        self.update()
        return self.render()


class RequestTokenPage(BaseTokenPage):

    def update(self):

        try:
            o_request = self._checkRequest(self.request)

            consumer_key = o_request.get('oauth_consumer_key', None)
            consumer = self._checkConsumer(consumer_key)

            callback = o_request.get('oauth_callback')
            self._checkCallback(callback)

            self._verifyOAuthRequest(o_request, consumer, None)

            # create request token
            tm = zope.component.getMultiAdapter((self.context, self.request),
                ITokenManager)
            self.token = tm.generateRequestToken(consumer, o_request)
        except (BaseValueError, BaseInvalidError,), e:
            raise BadRequest(e.args[0])


class GetAccessTokenPage(BaseTokenPage):

    def update(self):
        o_request = self._checkRequest(self.request)

        try:
            o_request = self._checkRequest(self.request)

            consumer_key = o_request.get('oauth_consumer_key', None)
            consumer = self._checkConsumer(consumer_key)

            token_key = o_request.get('oauth_token', None)
            token = self._checkToken(token_key)

            self._verifyOAuthRequest(o_request, consumer, token)

            # Token creation will validate the request for the verifier,
            # which can raise error that needs to be caught.
            tm = zope.component.getMultiAdapter((self.context, self.request),
                ITokenManager)
            self.token = tm.generateAccessToken(consumer, o_request)

        except (BaseValueError, BaseInvalidError,), e:
            raise BadRequest(e.args[0])


class AuthorizeTokenPage(Form, BaseTokenPage):

    ignoreContext = True
    invalidTokenMessage = _(u'Invalid Token.')
    invalidConsumerMessage = _(
        u'Consumer associated with this key is invalid.')
    deniedMessage = _(
        u'Token has been denied.')
    token = None
    consumer = None
    consumer_key = ''
    description = ''
    verifier = ''
    statusTemplate = ViewPageTemplateFile(path('authorize_status.pt'))
    verifierTemplate = ViewPageTemplateFile(path('authorize_verifier.pt'))
    template = ViewPageTemplateFile(path('authorize_question.pt'))
    _errors = False

    def _update(self):
        token_key = self.request.form.get('oauth_token', None)
        token = self._checkToken(token_key)
        consumer = self._checkConsumer(token.consumer_key)
        self.token = token
        self.consumer = consumer
        self.consumer_key = consumer.key

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

        return super(AuthorizeTokenPage, self).update() 

    def renderContents(self):
        if self._errors:
            return self.statusTemplate()
        if self.verifier:
            return self.verifierTemplate()
        return super(AuthorizeTokenPage, self).renderContents()

    def scope(self):
        # XXX make this hook into the scope manager such that subclasses
        # can implement more friendly renderings of requested resources
        # in a more friendly way so that these views don't need to be
        # customized.
        return self.token.scope

    @button.buttonAndHandler(_('Grant access'), name='approve')
    def handleApprove(self, action):
        """\
        User approves this token.
        
        Redirect user to the callback URL to give the provider the OAuth
        Verifier key.
        """

        if self._errors or not self.token:
            return

        mt = getToolByName(self.context, 'portal_membership')
        user = mt.getAuthenticatedMember().id

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        tm.claimRequestToken(self.token, user)
        if not self.token.callback == 'oob':
            callback_url = self.token.get_callback_url()
            return self.request.response.redirect(callback_url)
        # handle oob
        self.verifier = self.token.verifier

    @button.buttonAndHandler(_('Deny access'), name='deny')
    def handleDeny(self, action):
        """\
        User denies this token
        """

        token_key = self.request.form.get('oauth_token', None)
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        tm.remove(token_key)
        if not self.token.callback == 'oob':
            callback_url = self.token.get_callback_url()
            return self.request.response.redirect(callback_url)
        self.status = self.deniedMessage
        self._errors = True
