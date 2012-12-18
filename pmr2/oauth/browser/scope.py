import zope.component
import zope.interface
from zope.app.component.hooks import getSite
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces import IPublishTraverse

from Acquisition import Implicit
from Products.CMFCore.utils import getToolByName

from z3c.form import field
from z3c.form import button

from pmr2.z3cform import form
from pmr2.z3cform import page

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import IContentTypeScopeManager
from pmr2.oauth.interfaces import IContentTypeScopeProfile
from pmr2.oauth.interfaces import _IDynamicSchemaInterface
from pmr2.oauth.scope import ContentTypeScopeProfile

from pmr2.oauth.browser.interfaces import IContentTypeScopeProfileAdd
from pmr2.oauth.browser.interfaces import IContentTypeScopeProfileEdit
from pmr2.oauth.browser.template import path, ViewPageTemplateFile


class ScopeEditForm(form.EditForm):
    """\
    For editing scope.
    """

    @property
    def fields(self):
        sm = self.getContent()
        # this assumes the scope manager implements the immediate 
        # interface and that it provides all the fields for it.
        inf = zope.component.providedBy(sm).interfaces().next()
        return field.Fields(inf)

    def update(self):
        super(ScopeEditForm, self).update()
        self.request['disable_border'] = True

    def getContent(self):
        sm = zope.component.getMultiAdapter(
            (self.context, self.request), IContentTypeScopeManager)
        return sm


class ContentTypeScopeManagerView(Implicit, page.SimplePage):

    template = ViewPageTemplateFile(path('ctsm_view.pt'))

    @property
    def url_expr(self):
        # URL expression for this view.
        return '%s/%s' % (self.context.absolute_url(), self.__name__)


    def getContent(self):
        sm = zope.component.getMultiAdapter(
            (self.context, self.request), IContentTypeScopeManager)
        return sm

    def getProfileNames(self):
        """
        Return a unified list of the active profiles and WIP ones.
        """

        sm = self.getContent()
        pn = sm.getMappingNames()
        epn = sm.getEditProfileNames()
        # could yield this value, but it's small so save effort and be
        # naive.
        return sorted(list(set(list(pn) + list(epn))))

    def publishTraverse(self, request, name):
        # Since this is registerd as a view and is Implicit, it needs
        # this or this doesn't get resolved.
        return self


class ContentTypeScopeProfileTraverseForm(form.Form, page.TraversePage):

    def update(self):
        self.request['disable_border'] = True
        super(ContentTypeScopeProfileTraverseForm, self).update()

    def getContent(self):
        # only do this once.
        if not hasattr(self, '_content'):
            self._source = self.getSource()
        return self._source

    def getSource(self):
        if not self.traverse_subpath:
            raise NotFound(self.context, '')

        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        name = self.traverse_subpath[0]
        obj = sm.getEditProfile(name)
        if obj is None:
            raise NotFound(self.context, name)
        return obj


class ContentTypeScopeProfileDisplayForm(ContentTypeScopeProfileTraverseForm):

    #template = ViewPageTemplateFile(path('ctsp_view.pt'))

    #fields = field.Fields(IContentTypeScopeProfile)

    @button.buttonAndHandler(_('Edit'), name='edit')
    def handleEdit(self, action):
        pass

    @button.buttonAndHandler(_('Commit Update'), name='commit')
    def handleCommit(self, action):
        pass

    @button.buttonAndHandler(_('Revert'), name='revert')
    def handleRevert(self, action):
        pass


class ContentTypeScopeProfileEditForm(form.EditForm,
        ContentTypeScopeProfileTraverseForm):

    fields = field.Fields(IContentTypeScopeProfileEdit)


class ContentTypeScopeProfileAddForm(form.AddForm):
    
    fields = field.Fields(IContentTypeScopeProfileAdd)

    def create(self, data):
        result = ContentTypeScopeProfile()
        self._data = data
        return result

    def add(self, obj):
        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        sm.setEditProfile(self._data['name'], obj)

    def nextURL(self):
        return self.context.absolute_url()
