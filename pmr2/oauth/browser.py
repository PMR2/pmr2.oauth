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


class RequestTokenPage(BrowserPage):

    def __call__(self):
        o_request = zope.component.getAdapter(self.request, IRequest)

        if not o_request:
            raise BadRequest('missing oauth parameters')
        # XXX check and assemble a list of missing parameters.

        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)

        consumer = cm.get(o_request.get('oauth_consumer_key', None), None)
        if not consumer:
            raise BadRequest('invalid consumer key')

        utility = zope.component.getUtility(IOAuthUtility)
        try:
            params = utility.verify_request(o_request, consumer, None)
        except oauth.Error:
            raise BadRequest('could not verify oauth request.')

        # create token

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        token = tm.generateRequestToken(consumer, o_request)

        # return token
        return token.to_string()


class AuthorizeTokenPage(form.Form):

    ignoreContext = True
    invalidTokenMessage = _('Invalid Token.')
    invalidConsumerMessage = _('Consumer associated with this key is invalid.')
    token = None
    consumer = None
    consumer_key = ''
    description = ''
    statusTemplate = ViewPageTemplateFile('authorize_status.pt')
    template = ViewPageTemplateFile('authorize_question.pt')
    _errors = False

    def _checkToken(self, token_key):
        tokenid = self.request.form.get('oauth_token', None)
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        token = tm.get(token_key, None)
        if token is None:
            raise FormValueError(self.invalidTokenMessage)
        return token

    def _checkConsumer(self, consumer_key):
        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)
        consumer = cm.getValidated(consumer_key)
        if not consumer:
            raise FormValueError(self.invalidConsumerMessage)
        return consumer

    def _update(self):
        token = self._checkToken(self.request.form.get('oauth_token', None))
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
        except FormValueError, e:
            self.status = unicode(e)
            self._errors = True

        return super(AuthorizeTokenPage, self).update()

    def render(self):
        if self._errors:
            return self.statusTemplate()
        return super(AuthorizeTokenPage, self).render()

    @button.buttonAndHandler(_('Grant access'), name='approve')
    def handleApprove(self, action):
        """\
        User approves this token
        """

    @button.buttonAndHandler(_('Deny access'), name='deny')
    def handleDeny(self, action):
        """\
        User denies this token
        """
