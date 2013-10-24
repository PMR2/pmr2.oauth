import zope.component
import zope.interface

from Products.CMFCore.utils import getToolByName

from pmr2.z3cform import page

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.browser.template import path, ViewPageTemplateFile


class PMR2OAuthPage(page.SimplePage):

    template = ViewPageTemplateFile(path('pmr2-oauth.pt'))
    label = _(u'OAuth Provider Manager')

    @property
    def portal_url(self):
        portal_url = getToolByName(self.context, 'portal_url', None)
        if portal_url:
            portal = portal_url.getPortalObject()
            return portal.absolute_url()

    def isManager(self):
        mt = getToolByName(self.context, 'portal_membership')
        user = mt.getAuthenticatedMember()
        return user.has_role('Manager')

    def update(self):
        self.request['disable_border'] = True
