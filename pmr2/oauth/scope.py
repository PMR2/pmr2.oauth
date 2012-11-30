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

    def validate(self, context, client_key, access_key):
        """
        See IScopeManager.validate
        """

        raise NotImplemented


class DefaultScopeManager(ScopeManager):
    """\
    Default scope manager.

    The default scope manage only checks whether the path listed in the
    token matches the ones that are allowed, which are stored as a list
    in this manager.
    """

    zope.interface.implements(IDefaultScopeManager)
    permitted = fieldproperty.FieldProperty(IDefaultScopeManager['permitted'])

    def __init__(self):
        pass

    def _getPermittedList(self):
        # XXX memoize?
        if self.permitted:
            return self.permitted.splitlines()
        return []

    def _compileRegex(self):
        # XXX memoize?
        results = []
        for s in self._getPermittedList():
            if not s:
                # omit empty lines
                continue

            try:
                p = re.compile(s)
            except:
                # assume can't be compiled
                continue
            results.append(p)

        return results

    def validate(self, context, client_key, access_key):
        url = None
        valid_scopes = self._compileRegex()
        if not valid_scopes:
            # To be on the safe side, scopes must be defined.
            return False

        for vs in valid_scopes:
            if vs.search(url):
                return True

        # we got nothing, bad scope
        return False

DefaultScopeManagerFactory = factory(DefaultScopeManager)
