import re
import logging

from persistent import Persistent
from BTrees.OOBTree import OOBTree
from BTrees.IOBTree import IOBTree
from BTrees.OIBTree import OIBTree

from zope.container.contained import Contained
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
logger = logging.getLogger('pmr2.oauth.scope')


class BaseScopeManager(object):
    """
    Base scope manager.

    The base scope manager, does nothing on its own, can be used as a
    boilerplate for other scope managers.
    """

    zope.interface.implements(IScopeManager)
    
    def __init__(self, *a, **kw):
        pass

    def setScope(self, key, scope):
        raise NotImplementedError()

    def getScope(self, key, default=_marker):
        raise NotImplementedError()

    def popScope(self, key, default=_marker):
        raise NotImplementedError()

    def setClientScope(self, client_key, scope):
        raise NotImplementedError()

    def setAccessScope(self, access_key, scope):
        raise NotImplementedError()

    def getClientScope(self, client_key, default):
        raise NotImplementedError()

    def getAccessScope(self, access_key, default):
        raise NotImplementedError()

    def delClientScope(self, client_key):
        raise NotImplementedError()

    def delAccessScope(self, access_key):
        raise NotImplementedError()

    def validate(self, request, client_key, access_key,
            accessed, container, name, value):
        raise NotImplementedError()

    def requestScope(self, request_key, raw_scope):
        raise NotImplementedError()


class BTreeScopeManager(Persistent, Contained, BaseScopeManager):
    """
    Basic BTree based client/access scope manager.

    Provides mapping of client and access keys to a scope, but does not
    provide any validation capabilities.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)

    client_prefix = 'client.'
    access_prefix = 'access.'

    def __init__(self):
        self._scope = OOBTree()

    def setScope(self, key, scope):
        if self._scope.get(key, _marker) != _marker:
            raise KeyExistsError()
        self._scope[key] = scope

    def getScope(self, key, default=_marker):
        result = self._scope.get(key, default)
        if result == _marker:
            raise KeyError()
        return result

    def popScope(self, key, default=_marker):
        result = self._scope.pop(key, default)
        return result

    def setClientScope(self, client_key, scope):
        key = self.client_prefix + client_key
        self.setScope(key, scope)

    def setAccessScope(self, access_key, scope):
        key = self.access_prefix + access_key
        self.setScope(key, scope)

    def getClientScope(self, client_key, default=_marker):
        key = self.client_prefix + client_key
        return self.getScope(key, default)

    def getAccessScope(self, access_key, default=_marker):
        key = self.access_prefix + access_key
        return self.getScope(key, default)

    def delClientScope(self, client_key, default=_marker):
        key = self.client_prefix + client_key
        result = self.popScope(key, default)
        if result == _marker:
            raise KeyError()

    def delAccessScope(self, access_key, default=_marker):
        key = self.access_prefix + access_key
        result = self.popScope(key, default)
        if result == _marker:
            raise KeyError()

    def requestScope(self, request_key, raw_scope):
        """
        Requesting scope for this key.
        """

        # No reason or means to refuse this request as this doesn't do
        # any kind of management.
        self.setScope(request_key, raw_scope)
        return True


class ContentTypeScopeManager(BTreeScopeManager):
    """
    A scope manager based on content types.

    This scope manager validates the request using the content type of
    the accessed object and the subpath of the request against a content
    type mapping.  The content type mapping to be used will be one of
    specified by the resource access key, the client key or default, and
    is resolved in this order.

    One more restriction imposed by this scope manager: mappings are
    enforced absolutely for access keys.  This allows clients to request
    new default scopes for themselves at will and/or have site-wide
    default scope changes without compromising the scopes already
    granted by the resource owner referenced by the access key.

    This however does not address the case where additional global
    restrictions that may be placed by the site owner as the focus is
    ultimately on the access keys.  Workaround is to revoke those keys
    and have the content owners issue new ones regardless of changes.

    Pruning of unused scope is not implemented.
    """

    zope.interface.implements(IContentTypeScopeManager)

    default_mapping_id = fieldproperty.FieldProperty(
        IContentTypeScopeManager['default_mapping_id'])

    def __init__(self):
        super(ContentTypeScopeManager, self).__init__()
        self._mappings = IOBTree()

        # Methods permitted to access this mapping with.  Originally
        # I wanted to provide alternative sets of mapping on a per
        # mapping_id basis, however this proved to be complex and
        # complicated due to extra relationships involved.
        self._methods = IOBTree()

        # For metadata related to the above.
        self._mappings_metadata = IOBTree()

        # To ease the usage of scopes, the mappings are referenced by
        # names and are called profiles which add a few useful fields to
        # allow slightly easier usage.  This separates the name from the
        # already active tokens such that once a token is instantiated
        # with a scope, the mapping is stuck until the token is revoked.
        self._named_mappings = OIBTree()  # name to id.

        # To not overburden the named mappings with work-in-progress
        # profiles, instantiate one here also.
        self._edit_mappings = OOBTree()

        self.default_mapping_id = self.addMapping({})

    # Main mapping related management methods.

    def addMapping(self, mapping, methods='GET HEAD OPTIONS', metadata=None):
        key = 0  # default?
        if len(self._mappings) > 0:
            # Can calculate the next key.
            key = self._mappings.maxKey() + 1
        self._mappings[key] = mapping
        self._methods[key] = methods.split()
        if metadata is not None:
            self._mappings_metadata[key] = metadata
        return key

    def getMapping(self, mapping_id, default=_marker):
        result = self._mappings.get(mapping_id, default)
        if result is _marker:
            raise KeyError()
        return result

    def getMappingMetadata(self, mapping_id, default=None):
        result = self._mappings_metadata.get(mapping_id, default)
        return result

    def getMappingId(self, name):
        # Returned ID could potentially not exist, what do?
        return self._named_mappings[name]

    def getMappingMethods(self, mapping_id, default=_marker):
        result = self._methods.get(mapping_id, default)
        if result is _marker:
            raise KeyError()
        return result

    def checkMethodPermission(self, mapping_id, method):
        methods = self.getMappingMethods(mapping_id, ())
        return method in methods

    def setMappingNameToId(self, name, mapping_id):
        self._named_mappings[name] = mapping_id

    def delMappingName(self, name):
        saved = self._named_mappings.pop(name, None)
        edits = self._edit_mappings.pop(name, None)
        return (saved, edits)

    def getMappingByName(self, name, default=_marker):
        try:
            mapping_id = self.getMappingId(name)
            mapping = self.getMapping(mapping_id)
        except KeyError:
            if default == _marker:
                raise
            mapping = default
        return mapping

    def getMappingNames(self):
        return self._named_mappings.keys()

    # Temporary/edited mapping profiles

    def getEditProfile(self, name, default=None):
        return self._edit_mappings.get(name, default)

    def setEditProfile(self, name, value):
        assert IContentTypeScopeProfile.providedBy(value) or value is None
        self._edit_mappings[name] = value

    def commitEditProfile(self, name):
        profile = self.getEditProfile(name)
        if not (IContentTypeScopeProfile.providedBy(profile)):
            raise KeyError('edit profile does not exist')
        new_mapping = profile.mapping
        methods = profile.methods
        metadata = {
            'title': profile.title,
            'description': profile.description,
            # Should really not duplicate this there but this is easy
            # shortcut to take for now.
            'methods': methods,
        }
        new_id = self.addMapping(new_mapping, methods=methods,
            metadata=metadata)
        self.setMappingNameToId(name, new_id)

    def getEditProfileNames(self):
        return self._edit_mappings.keys()

    def isProfileModified(self, name):
        # TODO I would like some way to compare the two profiles in a
        # sane way but only using active types and types that have
        # stuff assigned.  So for now just use this naive method.
        profile = self.getEditProfile(name)
        try:
            mapping_id = self.getMappingId(name)
            mapping = self.getMapping(mapping_id)
            metadata = self.getMappingMetadata(mapping_id, {})
        except KeyError:
            # If profile exists, no associated ID, definitely modified.
            return True

        return not (profile.mapping == mapping and 
            profile.title == metadata.get('title') and
            profile.description == metadata.get('description') and
            profile.methods == metadata.get('methods')
        )

    # Scope handling.

    def requestScope(self, request_key, raw_scope):
        """
        This manager references scope by ids internally.  Resolve the
        raw scope id by the client into the mapping ids.
        """

        raw_scopes = raw_scope and raw_scope.split(',') or []
        result = set()
        for rs in raw_scopes:
            # Ignoring the current site URI and just capture the final
            # fragment.
            name = rs.split('/')[-1]
            try:
                mapping_id = self.getMappingId(name)
                # This verifies the existence of the mapping with id.
                mapping = self.getMapping(mapping_id)
            except KeyError:
                # Failed to fulfill the requested scope.
                return False
            result.add(mapping_id)

        if not result:
            result.add(self.default_mapping_id)

        self.setScope(request_key, result)
        return True

    def validate(self, request, client_key, access_key,
            accessed, container, name, value):
        """
        See IScopeManager.
        """

        mappings = self.resolveMapping(client_key, access_key)
        # multiple rights were requested, check through all of them.
        for mapping_id in mappings:
            mapping = self.getMapping(mapping_id, default={})
            result = self.validateTargetWithMapping(accessed, name, mapping)
            method_allowed = self.checkMethodPermission(mapping_id,
                request.method)
            if result and method_allowed:
                return True

        # no matching mappings.
        return False

    def resolveMapping(self, client_key, access_key):
        """
        See IDefaultScopeManager.
        """

        # As all mappings are referenced byh access keys.
        return self.getAccessScope(access_key, None)

    def resolveTarget(self, accessed, name):
        """
        Accessed target resolution.

        Find the type of the container object of the accessed object by
        traversing upwards, and gather the path to resolve into the 
        content type id.  Return both these values.
        """

        logger.debug('resolving %s into types', accessed)
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

        logger.debug('parent of %s failed to resolve into typeinfo', accessed)
        return None, None

    def validateTargetWithMapping(self, accessed, name, mapping):
        atype, subpath = self.resolveTarget(accessed, name)
        return self.validateTypeSubpathMapping(atype, subpath, mapping)

    def validateTypeSubpathMapping(self, accessed_type, subpath, mapping):
        # A simple lookup method.
        valid_scopes = mapping.get(accessed_type, {})
        if not valid_scopes:
            logger.debug('out of scope: %s has no mapping', accessed_type)
            return False
        logger.debug('%s got mapping', accessed_type)

        for vs in valid_scopes:
            # XXX ignores second last asterisk, preventing validation
            # against items that have an asterisk in its name for 
            # whatever reason...
            if vs.endswith('*') and '/' in vs:
                match = subpath.startswith(vs[:vs.rindex('*')])
            else:
                match = subpath == vs
            if match:
                logger.debug('subpath:%s within scope', subpath)
                return True
        logger.debug('out of scope: %s not a subpath in mapping for %s',
            subpath, accessed_type)
        return False

ContentTypeScopeManagerFactory = factory(ContentTypeScopeManager)


class ContentTypeScopeProfile(Persistent):
    """
    The one for editing purpose.  Allows definition of names and fields
    related to the user side creation and usage of mappings.
    """

    zope.interface.implements(IContentTypeScopeProfile)

    title = fieldproperty.FieldProperty(
        IContentTypeScopeProfile['title'])
    description = fieldproperty.FieldProperty(
        IContentTypeScopeProfile['description'])
    methods = fieldproperty.FieldProperty(IContentTypeScopeProfile['methods'])
    mapping = fieldproperty.FieldProperty(IContentTypeScopeProfile['mapping'])
