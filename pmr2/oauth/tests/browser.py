from zope.publisher.browser import BrowserPage
from Products.CMFCore.utils import getToolByName 


class CurrentUserView(BrowserPage):

    def __call__(self):
        mt = getToolByName(self.context, 'portal_membership')
        if mt.isAnonymousUser():
            return 'Anonymous User'
        user = mt.getAuthenticatedMember()
        return user.id


class CurrentRolesView(BrowserPage):

    def __call__(self):
        mt = getToolByName(self.context, 'portal_membership')
        roles = '\n'.join(mt.getAuthenticatedMember().getRoles())
        return roles


class OAuthCallbackView(BrowserPage):

    def __call__(self):
        verifier = 'Verifier: %s' % self.request.form.get('oauth_verifier')
        token = 'Token: %s' % self.request.form.get('oauth_token')
        return verifier + '\n' + token
