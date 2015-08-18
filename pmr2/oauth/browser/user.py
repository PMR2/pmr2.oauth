import zope.component
import zope.interface
from zope.publisher.browser import BrowserPage
from zope.component.hooks import getSite
from zope.publisher.interfaces import NotFound

from z3c.form import button

from Acquisition import Implicit
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from pmr2.z3cform import form, page

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import IConsumerManager, ITokenManager
from pmr2.oauth.interfaces import IContentTypeScopeManager, IScopeManager
from pmr2.oauth.browser.template import ViewPageTemplateFile
from pmr2.oauth.browser.template import path
from pmr2.oauth.browser.scope import TokenCTScopeView


class _NotConsumer(object):
     title = _(u'<Deleted Client>')


class BaseUserTokenForm(form.PostForm):
    """\
    For user to manage their authorized tokens.
    """

    ignoreContext = True
    template = ViewPageTemplateFile(path('user_manage_token.pt'))

    @property
    def url_expr(self):
        # URL expression for this view.
        return '%s/%s' % (self.context.absolute_url(), self.__name__)

    def getUser(self):
        # Returns the current user, or the target user.
        raise NotImplemented

    def getTokens(self):
        user = self.getUser()
        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        tokens = []
        for token in tm.getTokensForUser(user):
            consumer_title = cm.get(token.consumer_key, _NotConsumer).title
            tokens.append({
                'consumer_title': consumer_title,
                'key': token.key,
            })
        return tokens

    def update(self):
        super(BaseUserTokenForm, self).update()
        self.tokens = self.getTokens()
        self.request['disable_border'] = True

    def revokeTokens(self):
        """
        User revokes selected tokens.
        """

        # manually do everything since we are not using the built-in
        # widgets
        # TODO use widgets?

        current_user = self.getUser()
        valid = self.getTokens()
        removed = error = 0
        keys = self.request.form.get('form.widgets.key', [])
        if isinstance(keys, basestring):
            # don't cast a string into a list as we are expecting one.
            keys = [keys]
        
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        sm = zope.component.getMultiAdapter((self.context, self.request),
            IScopeManager)

        for k in keys:
            token = tm.get(k)
            if token is None or not token.user == current_user:
                error = 1
                continue

            try:
                tm.remove(k)
                sm.delAccessScope(k, None)
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


def hasTokens(form):
    # need this separate method with separate checks because this must be
    # executed independently, until after any other action has been done.
    user = form.getUser()
    tm = zope.component.getMultiAdapter((form.context, form.request),
        ITokenManager)
    return tm.hasTokensForUser(user)


class UserTokenForm(BaseUserTokenForm):

    def getUser(self):
        mt = getToolByName(self.context, 'portal_membership')
        return mt.getAuthenticatedMember().id

    @button.buttonAndHandler(_('Revoke'), name='revoke', condition=hasTokens)
    def handleRevoke(self, action):
        data, errors = self.extractData()
        return self.revokeTokens()


class UserTokenListView(Implicit, BrowserPage):

    def publishTraverse(self, request, name):
        # viewlet manager doesn't seem to like implicit objects, so this
        # and the above has to be split up...
        result = UserTokenForm(self.context, self.request)
        result.__name__ = self.__name__
        return result


class UserTokenCTScopeDetailsView(page.TraversePage, TokenCTScopeView):
    """
    This view class explicitly includes ContentTypeScope informations.
    Plugins that wish to override this scope manager will also need to
    override this view appropriately with the use of layers.
    """

    template = ViewPageTemplateFile(path('token_scope_view.pt'))

    def getTokenKey(self):
        if not self.traverse_subpath or len(self.traverse_subpath) > 1:
            return None
        return self.traverse_subpath[0]

    def getScope(self, token_key):
        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        # scopes for this manager is a set of mapping_ids.
        return sm.getAccessScope(token_key, None)

    def update(self):
        site = getSite()
        tm = zope.component.getMultiAdapter(
            (site, self.request), ITokenManager)
        cm = zope.component.getMultiAdapter(
            (site, self.request), IConsumerManager)
        token_key = self.getTokenKey()
        token = tm.getAccessToken(token_key, None)

        mt = getToolByName(self.context, 'portal_membership')
        current_user = mt.getAuthenticatedMember().id

        if token is None or not token.user == current_user:
            raise NotFound(self.context, token_key)

        self.consumer_title = cm.get(token.consumer_key, _NotConsumer).title

        # Set the scope attributes only after this token is found for
        # this user.
        super(UserTokenCTScopeDetailsView, self).update()
