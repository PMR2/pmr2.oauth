import re

from persistent import Persistent

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
import zope.interface
from zope.schema import fieldproperty

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
    permitted = fieldproperty.FieldProperty(IDefaultScopeManager['permitted'])

    def validate(self, client_key, access_key, container, name, **kw):
        valid_scopes = self.permitted or []
        return name in valid_scopes

DefaultScopeManagerFactory = factory(DefaultScopeManager)
