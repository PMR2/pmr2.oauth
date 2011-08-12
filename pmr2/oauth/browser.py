import oauth2 as oauth

import zope.component
from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zExceptions import BadRequest
from zExceptions import Forbidden
from zExceptions import Unauthorized

from z3c.form import form
from z3c.form import button
from plone.z3cform import layout

from Products.CMFCore.utils import getToolByName

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import *


class BaseTokenPage(BrowserPage):

    def _checkRequest(self, request):
        o_request = zope.component.getAdapter(request, IRequest)

        if not o_request:
            raise RequestInvalidError('missing oauth parameters')
        # XXX check and assemble a list of missing parameters.

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

    def _verifyRequest(self, o_request, consumer, token):
        utility = zope.component.getUtility(IOAuthUtility)
        try:
            params = utility.verify_request(o_request, consumer, token)
        except oauth.Error, e:
            raise RequestInvalidError(e.message)
        return True


class RequestTokenPage(BaseTokenPage):

    def __call__(self):

        try:
            o_request = self._checkRequest(self.request)
            consumer_key = o_request.get('oauth_consumer_key', None)
            consumer = self._checkConsumer(consumer_key)
            self._verifyRequest(o_request, consumer, None)
        except (BaseValueError, BaseInvalidError,), e:
            raise BadRequest(e.args[0])

        # create token

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        token = tm.generateRequestToken(consumer, o_request)

        # return token
        return token.to_string()


class GetAccessTokenPage(BaseTokenPage):

    def __call__(self):
        o_request = self._checkRequest(self.request)

        try:
            o_request = self._checkRequest(self.request)

            consumer_key = o_request.get('oauth_consumer_key', None)
            consumer = self._checkConsumer(consumer_key)

            token_key = o_request.get('oauth_token', None)
            token = self._checkToken(token_key)

            self._verifyRequest(o_request, consumer, token)

            # token creation will validate the request for the verifier.
            tm = zope.component.getMultiAdapter((self.context, self.request),
                ITokenManager)
            token = tm.generateAccessToken(consumer, o_request)

        except (BaseValueError, BaseInvalidError,), e:
            raise BadRequest(e.args[0])

        # return token
        return token.to_string()


class AuthorizeTokenPage(form.Form, BaseTokenPage):

    ignoreContext = True
    invalidTokenMessage = _(u'Invalid Token.')
    invalidConsumerMessage = _(
        u'Consumer associated with this key is invalid.')
    token = None
    consumer = None
    consumer_key = ''
    description = ''
    statusTemplate = ViewPageTemplateFile('authorize_status.pt')
    template = ViewPageTemplateFile('authorize_question.pt')
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

    def render(self):
        if self._errors:
            return self.statusTemplate()
        return super(AuthorizeTokenPage, self).render()

    @button.buttonAndHandler(_('Grant access'), name='approve')
    def handleApprove(self, action):
        """\
        User approves this token.  Redirect user to the callback URL to
        give the provider the OAuth Verifier key.
        """

        if self._errors or not self.token:
            return
        return self.request.response.redirect(self.token.get_callback_url())

    @button.buttonAndHandler(_('Deny access'), name='deny')
    def handleDeny(self, action):
        """\
        User denies this token
        """


