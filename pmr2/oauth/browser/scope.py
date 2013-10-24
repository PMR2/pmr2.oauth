import zope.component
import zope.interface
from zope.component.hooks import getSite
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces import IPublishTraverse

from Acquisition import Implicit
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from z3c.form import field
from z3c.form import button
from z3c.form.interfaces import DISPLAY_MODE

from pmr2.z3cform import form
from pmr2.z3cform import page

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import IScopeManager, IContentTypeScopeManager
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

    template = ViewPageTemplateFile(path('ctsm_root.pt'))

    def update(self):
        self.request['disable_border'] = True

    @property
    def label(self):
        return _(u'Content Type Scope Manager')

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


class ContentTypeScopeProfileTraverseForm(form.AuthenticatedForm,
        page.TraversePage):
    # TODO split the form specific part up.

    def _getProfileAndMapping(self):
        profile = self.getContent()
        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        mapping = sm.getMappingByName(self.profile_name, default={})
        return profile, mapping

    @property
    def profile_name(self):
        if not self.traverse_subpath or len(self.traverse_subpath) > 1:
            return None

        return self.traverse_subpath[0]

    def update(self):
        self.request['disable_border'] = True
        super(ContentTypeScopeProfileTraverseForm, self).update()

    def getContent(self):
        # only do this once.
        if not hasattr(self, '_content'):
            self._source = self.getSource()
        return self._source

    def getSource(self):
        name = self.profile_name
        if not name:
            raise NotFound(self.context, '')

        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        obj = sm.getEditProfile(name)
        if obj is None:
            raise NotFound(self.context, name)
        return obj


class ContentTypeScopeProfileDisplayForm(ContentTypeScopeProfileTraverseForm):

    # TODO At some point we should consider rendering the content-type
    # icons.
    template = ViewPageTemplateFile(path('ctsp_view.pt'))

    fields = field.Fields(IContentTypeScopeProfileEdit)
    mode = DISPLAY_MODE
    next_target = None

    @button.buttonAndHandler(_('Edit'), name='edit')
    def handleEdit(self, action):
        self.authenticate()
        if self.profile_name:
            # absolute_url is implicitly acquired by the parent view.
            self.next_target = '/'.join([self.context.absolute_url(), 
                self.context.__name__, 'edit', self.profile_name,])

    @button.buttonAndHandler(_('Commit Update'), name='commit')
    def handleCommit(self, action):
        self.authenticate()
        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        sm.commitEditProfile(self.profile_name)

        self.next_target = '/'.join([self.context.absolute_url(), 
            self.context.__name__, 'view', self.profile_name,])

    @button.buttonAndHandler(_('Revert'), name='revert')
    def handleRevert(self, action):
        self.authenticate()
        profile, original = self._getProfileAndMapping()
        profile.mapping = original

        self.next_target = '/'.join([self.context.absolute_url(), 
            self.context.__name__, 'view', self.profile_name,])

    @button.buttonAndHandler(_('Set as Default'), name='setdefault')
    def handleSetDefault(self, action):
        self.authenticate()
        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        try:
            sm.default_mapping_id = sm.getMappingId(self.profile_name)
        except KeyError:
            status = IStatusMessage(self.request)
            status.addStatusMessage(_(
                u'This profile has not been committed yet.'),
                'error'
            )

        self.next_target = '/'.join([self.context.absolute_url(), 
            self.context.__name__, 'view', self.profile_name,])

    def update(self):
        super(ContentTypeScopeProfileDisplayForm, self).update()

        if self.isMappingModified():
            status = IStatusMessage(self.request)
            status.addStatusMessage(_(
                u'This profile has been modified.  Please commit the changes '
                 'when they are ready.'),
                'info'
            )

        if self.next_target:
            self.request.response.redirect(self.next_target)

    def isMappingModified(self):
        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        return sm.isProfileModified(self.profile_name)


class ContentTypeScopeProfileEditForm(form.EditForm,
        ContentTypeScopeProfileTraverseForm):

    fields = field.Fields(IContentTypeScopeProfileEdit)

    buttons = form.EditForm.buttons.copy()
    handlers = form.EditForm.handlers.copy()

    @button.buttonAndHandler(_('Cancel and Return'), name='cancel')
    def handleCancel(self, action):
        data, errors = self.extractData()
        next_target = '/'.join([self.context.absolute_url(), 
            self.context.__name__, 'view', self.profile_name,])
        self.request.response.redirect(next_target)


class ContentTypeScopeProfileAddForm(form.AddForm):
    
    fields = field.Fields(IContentTypeScopeProfileAdd)

    def update(self):
        self.request['disable_border'] = True
        super(ContentTypeScopeProfileAddForm, self).update()

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
        return '/'.join([self.context.absolute_url(), 
            self.context.__name__, 'view', self._data['name'],])


class BaseTokenScopeView(page.SimplePage):

    @property
    def label(self):
        return _(u'Token Scope Information')

    def getTokenKey(self):
        return self.request.get('oauth_token')

    def getScope(self, token_key):
        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IScopeManager)
        return sm.getScope(token_key, None)

    def template(self):
        # This should cause the parent template to render a notification
        return u''

    def getTokenScopeInfo(self):
        # basically check for the existent of the scope.
        token_key = self.getTokenKey()
        if not token_key:
            raise NotFound(self.context, '')

        scope = self.getScope(token_key)
        if not scope:
            raise NotFound(self.context, '')

        return token_key, scope

    def update(self):
        token_key, scope = self.getTokenScopeInfo()


class TokenCTScopeView(BaseTokenScopeView):

    template = ViewPageTemplateFile(path('token_scope_view.pt'))
    missing_metadata = {
        'title': _(u'<Undefined Mapping Type>'),
        'description': u'',
    }

    @property
    def label(self):
        return _(u'Token Scope Information')

    def getScope(self, token_key):
        """
        Override to ensure the correct scope manager is returned.
        """

        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)
        # scopes for this manager is a set of mapping_ids.
        return sm.getScope(token_key, None)

    def update(self):
        token_key, mapping_ids = self.getTokenScopeInfo()
        self.request['disable_border'] = True

        site = getSite()
        sm = zope.component.getMultiAdapter(
            (site, self.request), IContentTypeScopeManager)

        # merge the mappings and the profiles.
        all_maps = {}
        writable_maps = {}
        mapping_metadata = []
        mapping_keys = ('portal_type', 'subpaths')
        write_methods = set(('POST', 'PUT', 'DELETE',))
        for mapping_id in mapping_ids:

            # mappings
            mapping = sm.getMapping(mapping_id)
            writable = set(sm.getMappingMethods(mapping_id)
                ).intersection(write_methods)
            for pt, subpaths in mapping.iteritems():
                if not subpaths:
                    continue
                if not pt in all_maps:
                    all_maps[pt] = []
                all_maps[pt].extend(subpaths)

                if writable:
                    if not pt in writable_maps:
                        writable_maps[pt] = []
                    writable_maps[pt].extend(subpaths)

            # profiles
            metadata = sm.getMappingMetadata(mapping_id)
            if not metadata:
                metadata = self.missing_metadata
            mapping_metadata.append(metadata)

        self.mappings = [dict(zip(mapping_keys, (k, sorted(list(set(p))))))
                         for k, p in sorted(all_maps.items())]
        self.writable_mappings = [dict(zip(mapping_keys,
                                           (k, sorted(list(set(p))))))
                                  for k, p in sorted(writable_maps.items())]
        self.hasWritableMappings = len(self.writable_mappings) > 0
        self.profiles = sorted(mapping_metadata,
            lambda a, b: cmp(a['title'], b['title']))
