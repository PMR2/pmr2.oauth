import zope.component
import zope.interface
from zope.publisher.browser import BrowserPage

from z3c.form import form
from z3c.form import button

from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import *
from pmr2.oauth.browser.template import ViewPageTemplateFile
from pmr2.oauth.browser.template import path
from pmr2.oauth.browser.form import Form


class BaseUserTokenForm(Form):
    """\
    For user to manage their authorized tokens.
    """

    ignoreContext = True
    template = ViewPageTemplateFile(path('user_manage_token.pt'))

    def getUser(self):
        raise NotImplemented

    def getTokens(self):
        user = self.getUser()
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        tokens = tm.getTokensForUser(user)
        # XXX need to process scope here into the string that user might
        # recognize.
        return tokens

    def update(self):
        super(BaseUserTokenForm, self).update()
        self.tokens = self.getTokens()
        self.request['disable_border'] = True

    @button.buttonAndHandler(_('Revoke'), name='revoke')
    def handleRevoke(self, action):
        """\
        User revokes selected tokens.
        """

        # manually do everything since we are not using the built-in
        # widgets
        # TODO use widgets?

        removed = error = 0
        keys = self.request.form.get('form.widgets.key', [])
        if isinstance(keys, basestring):
            # don't cast a string into a list as we are expecting one.
            keys = [keys]
        
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        for k in keys:
            try:
                tm.remove(k)
                removed += 1
            except:
                error = 1

        status = IStatusMessage(self.request)
        if error:
            status.addStatusMessage(
                _(u'Errors encountered during key removal'),
                type="error")
        if removed:
            status.addStatusMessage(
                _(u'Access successfully removed'),
                type="info")


class UserTokenForm(BaseUserTokenForm):

    def getUser(self):
        mt = getToolByName(self.context, 'portal_membership')
        return mt.getAuthenticatedMember().id
