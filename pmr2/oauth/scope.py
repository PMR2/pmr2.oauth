import re

from persistent import Persistent

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
import zope.interface
from zope.schema import fieldproperty

from Acquisition import aq_parent, aq_inner
from Products.CMFCore.utils import getToolByName

from pmr2.oauth.interfaces import IScopeManager, IDefaultScopeManager
from pmr2.oauth.interfaces import IDefaultScopeProfile
from pmr2.oauth.factory import factory


class ScopeManager(object):
    """\
    Base scope manager.

    The base scope manager, does nothing on its own, can be used as a
    boilerplate for other scope managers.
    """

    zope.interface.implements(IScopeManager)
    
    def __init__(self):
        pass

    def storeClientScope(self, client_key, scope):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def storeAccessScope(self, access_key, scope):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def getClientScope(self, client_key):
        """
        See IScopeManager
        """

        raise NotImplementedError()

    def getAccessScope(self, access_key):
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


class DefaultScopeManager(Persistent, Contained, ScopeManager):
    """
    Default scope manager.

    The default scope manage only checks whether the name listed in the
    token matches the ones that are allowed, which are stored as a list
    in this manager.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)
    zope.interface.implements(IDefaultScopeManager)

    mappings = fieldproperty.FieldProperty(IDefaultScopeProfile['mappings'])

    def storeClientScope(self, client_key, scope):
        """
        See IScopeManager
        """

    def storeAccessScope(self, access_key, scope):
        """
        See IScopeManager
        """

    def getClientScope(self, client_key):
        """
        See IScopeManager
        """

    def getAccessScope(self, access_key):
        """
        See IScopeManager
        """

    def delClientScope(self, client_key):
        """
        See IScopeManager
        """

    def delAccessScope(self, access_key):
        """
        See IScopeManager
        """

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

DefaultScopeManagerFactory = factory(DefaultScopeManager)
