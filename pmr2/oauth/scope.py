import re

from persistent import Persistent

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
import zope.interface
from zope.schema import fieldproperty

from Acquisition import aq_parent, aq_inner
from Products.CMFCore.utils import getToolByName

from pmr2.oauth.interfaces import IScopeManager
from pmr2.oauth.interfaces import IDefaultScopeManager
from pmr2.oauth.factory import factory


class ScopeManager(Persistent, Contained):
    """\
    Base scope manager.

    The base scope manager, does nothing on its own, serve as a 
    boilerplate for other scope manager.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)
    zope.interface.implements(IScopeManager)
    
    def __init__(self):
        pass

    def validate(self, client_key, access_key, **kw):
        """
        See IScopeManager.validate
        """

        raise NotImplemented


class DefaultScopeManager(ScopeManager):
    """\
    Default scope manager.

    The default scope manage only checks whether the name listed in the
    token matches the ones that are allowed, which are stored as a list
    in this manager.
    """

    zope.interface.implements(IDefaultScopeManager)
    default_scopes = fieldproperty.FieldProperty(
        IDefaultScopeManager['default_scopes'])

    def resolveValues(self, container, name):
        # use getSite() instead of container?
        pt_tool = getToolByName(container, 'portal_types', None)
        if pt_tool is None:
            return

        context = aq_inner(container)
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

        return

    def validate(self, client_key, access_key, accessed, name, **kw):
        """
        Default validation.

        Ignore where the value was originally accessed from and focus
        on the accessed object.  Traverse up the parents until arrival 
        at a registered type, using the names to build the subpath, then
        check for its existence in the list of permitted scope for the 
        accessed object.
        """

        if not self.default_scopes:
            return False

        container_typeid, subpath = self.resolveValues(accessed, name)
        valid_scopes = self.default_scopes.get(container_typeid, {})
        if not valid_scopes:
            return False

        return subpath in valid_scopes

DefaultScopeManagerFactory = factory(DefaultScopeManager)
