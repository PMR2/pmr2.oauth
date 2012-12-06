import re

from persistent import Persistent
from BTrees.OOBTree import OOBTree

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
import zope.interface
from zope.schema import fieldproperty

from Acquisition import aq_parent, aq_inner
from Products.CMFCore.utils import getToolByName

from pmr2.oauth.interfaces import KeyExistsError
from pmr2.oauth.interfaces import IScopeManager, IDefaultScopeManager
from pmr2.oauth.interfaces import IContentTypeScopeManager
from pmr2.oauth.interfaces import IContentTypeScopeProfile
from pmr2.oauth.factory import factory

_marker = object()


class BaseScopeManager(object):
    """\
    Base scope manager.

    The base scope manager, does nothing on its own, can be used as a
    boilerplate for other scope managers.
    """

    zope.interface.implements(IScopeManager)
    
    def __init__(self):
        pass

    def setClientScope(self, client_key, scope):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def setAccessScope(self, access_key, scope):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def getClientScope(self, client_key, default=_marker):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def getAccessScope(self, access_key, default=_marker):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def delClientScope(self, client_key):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def delAccessScope(self, access_key):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def validate(self, client_key, access_key, **kw):
        """
        See IScopeManager
        """

        raise NotImplementedError()


class BTreeScopeManager(Persistent, Contained, BaseScopeManager):
    """
    Basic BTree based client/access scope manager.

    Provides mapping of client and access keys to a scope, but does not
    provide any validation capabilities.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)

    def __init__(self):
        self._client_scope = OOBTree()
        self._access_scope = OOBTree()

    def setClientScope(self, client_key, scope):
        if client_key in self._client_scope.keys():
            raise KeyExistsError()
        self._client_scope[client_key] = scope

    def setAccessScope(self, access_key, scope):
        if access_key in self._access_scope.keys():
            raise KeyExistsError()
        self._access_scope[access_key] = scope

    def getClientScope(self, client_key, default=_marker):
        result = self._client_scope.get(client_key, default)
        if result == _marker:
            raise KeyError()
        return result

    def getAccessScope(self, access_key, default=_marker):
        result = self._access_scope.get(access_key, default)
        if result == _marker:
            raise KeyError()
        return result

    def delClientScope(self, client_key, default=_marker):
        result = self._client_scope.pop(client_key, default)
        if result == _marker:
            raise KeyError()

    def delAccessScope(self, access_key, default=_marker):
        result = self._access_scope.pop(access_key, default)
        if result == _marker:
            raise KeyError()


class ContentTypeScopeManager(BTreeScopeManager):
    """
    A scope manager based on content types.

    This scope manager validates the request using the content type of
    the accessed object and the subpath of the request against a content
    type profile.  The content type profile to be used will be one of
    specified by the resource access key, the client key or default, and
    is resolved in this order.
    """

    zope.interface.implements(IContentTypeScopeManager)

    mappings = fieldproperty.FieldProperty(
        IContentTypeScopeProfile['mappings'])

    def validate(self, client_key, access_key,
            accessed, container, name, value):
        """
        See IScopeManager.
        """

        accessed_typeid, subpath = self.resolveTarget(accessed, name)
        profile = self.resolveProfile(client_key, access_key)
        return self.validateTargetWithProfile(
            accessed_typeid, subpath, profile)

    def resolveProfile(self, client_key, access_key):
        """
        See IDefaultScopeManager.
        """

        # XXX placeholder
        return self

    def resolveTarget(self, accessed, name):
        # use getSite() instead of container?
        pt_tool = getToolByName(accessed, 'portal_types', None)
        if pt_tool is None:
            return None, None

        context = aq_inner(accessed)
        typeinfo = None
        subpath = [name]

        while context is not None:
            typeinfo = pt_tool.getTypeInfo(context)
            if typeinfo:
                subpath.reverse()
                return typeinfo.id, '/'.join(subpath)
            # It should have a name...
            subpath.append(context.__name__)
            context = aq_parent(context)

        return None, None

    def validateTargetWithProfile(self, accessed_typeid, subpath, profile):
        """
        Default validation.

        Ignore where the value was originally accessed from and focus
        on the accessed object.  Traverse up the parents until arrival 
        at a registered type, using the names to build the subpath, then
        check for its existence in the list of permitted scope for the 
        accessed object.
        """

        mappings = profile.mappings
        if not mappings:
            return False

        valid_scopes = mappings.get(accessed_typeid, {})
        if not valid_scopes:
            return False

        return subpath in valid_scopes

ContentTypeScopeManagerFactory = factory(ContentTypeScopeManager)


class ContentTypeScopeProfile(object):

    zope.interface.implements(IContentTypeScopeProfile)
