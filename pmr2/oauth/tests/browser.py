from zope.publisher.browser import BrowserPage
from Products.CMFCore.utils import getToolByName 


class CurrentUserView(BrowserPage):

    def __call__(self):
        mt = getToolByName(self.context, 'portal_membership')
        if mt.isAnonymousUser():
            return 'Anonymous User'
        user = mt.getAuthenticatedMember()
        return user.id
