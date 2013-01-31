from time import time
import unittest

from zope.interface import Interface
import zope.component
from zope.schema.interfaces import WrongType, WrongContainedType

from zExceptions import Forbidden
from zExceptions import BadRequest

from Products.PloneTestCase import ptc

from pmr2.oauth.interfaces import KeyExistsError
from pmr2.oauth.interfaces import IDefaultScopeManager
from pmr2.oauth.scope import BTreeScopeManager, ContentTypeScopeManager
from pmr2.oauth.scope import ContentTypeScopeProfile

from pmr2.oauth.tests import base


class BTreeScopeManagerTestCase(unittest.TestCase):
    """
    Test the storage and retrieval of client and access key specific
    scopes.
    """

    def setUp(self):
        self.sm = BTreeScopeManager()
        self.client = 'client_key'
        self.access = 'access_key'

    def test_0000_base(self):
        self.assertRaises(KeyError, self.sm.delClientScope, self.client)
        self.assertRaises(KeyError, self.sm.delAccessScope, self.access)

        self.assertRaises(KeyError, self.sm.getClientScope, self.client)
        self.assertRaises(KeyError, self.sm.getAccessScope, self.access)

        self.assertTrue(
            self.sm.getClientScope(self.client, default=None) is None)
        self.assertTrue(
            self.sm.getAccessScope(self.access, default=None) is None)

    def test_0010_set_get(self):
        scope1 = 'http://example.com/scope.1'
        scope2 = 'http://example.com/scope.2'

        self.sm.setClientScope(self.client, scope1)
        self.assertEqual(self.sm.getClientScope(self.client), scope1)

        self.sm.setAccessScope(self.access, scope2)
        self.assertEqual(self.sm.getAccessScope(self.access), scope2)

    def test_0011_set_duplicate(self):
        scope1 = 'http://example.com/scope.1'
        scope2 = 'http://example.com/scope.2'

        self.sm.setClientScope(self.client, scope1)
        self.assertRaises(KeyExistsError, 
            self.sm.setClientScope, self.client, scope1)

        self.sm.setAccessScope(self.access, scope2)
        self.assertRaises(KeyExistsError, 
            self.sm.setAccessScope, self.access, scope2)

    def test_0020_del(self):
        scope1 = 'http://example.com/scope.1'
        scope2 = 'http://example.com/scope.2'

        self.sm.setClientScope(self.client, scope1)
        self.sm.delClientScope(self.client)
        # Can "hide" exception using optional parameter like get/set.
        self.sm.delClientScope(self.client, None)
        self.sm.setClientScope(self.client, scope2)
        self.assertEqual(self.sm.getClientScope(self.client), scope2)

        self.sm.setAccessScope(self.access, scope1)
        # This may be considered dangerous as this does not tie into the
        # access token in any way.  Subclasses may need to handle this
        # to ensure the content owner is aware of scope changes.
        self.sm.delAccessScope(self.access)

        # New scope is updated.
        self.sm.setAccessScope(self.access, scope2)
        self.assertEqual(self.sm.getAccessScope(self.access), scope2)


class CTSMMappingTestCase(unittest.TestCase):
    """
    Testing the profile and management within this scope manager.
    """

    def setUp(self):
        self.sm = ContentTypeScopeManager()
        self.file_mapping = {'File': ['document_view']}
        self.folder_mapping = {'Folder': ['folder_contents']}

    def test_0100_get_mapping(self):
        self.assertRaises(KeyError, self.sm.getMapping, 1)
        self.assertEqual(self.sm.getMapping(1, default='test'), 'test')

    def test_0101_add_get_mapping(self):
        self.assertEqual(self.sm.addMapping('test'), 1)
        self.assertEqual(self.sm.getMapping(1), 'test')

    def test_0200_mapping_name_and_id(self):
        _marker = 2
        self.assertRaises(KeyError, self.sm.getMappingId, 'rawscope')
        self.sm.setMappingNameToId('rawscope', _marker)
        self.assertEqual(self.sm.getMappingId('rawscope'), _marker)
        self.sm.setMappingNameToId('rawscope', 3)
        self.assertEqual(self.sm.getMappingId('rawscope'), 3)
        self.sm.delMappingName('rawscope')
        self.assertRaises(KeyError, self.sm.getMappingId, 'rawscope')

    def test_1000_request_scope_fresh_fail(self):
        self.assertFalse(self.sm.requestScope('key', 'rawscope'))
        self.assertEqual(len(self.sm._scope), 0)

    def test_1001_request_scope_fresh_default(self):
        self.assertTrue(self.sm.requestScope('key', None))
        self.assertEqual(len(self.sm._scope), 1)
        # Can't set this again.
        self.assertRaises(KeyError, self.sm.requestScope, 'key', None)

    def test_1002_request_scope_set_singular(self):
        key = 'request_key'
        scope = 'test_scope'
        mapping_id = self.sm.addMapping(self.file_mapping)
        self.sm.setMappingNameToId(scope, mapping_id)
        self.assertTrue(self.sm.requestScope(key, scope))
        self.assertEqual(len(self.sm._scope), 1)
        mappings = self.sm.getScope(key)
        self.assertEqual(len(mappings), 1)
        self.assertTrue(mapping_id in mappings)
        # Obviously not an access scope.
        self.assertRaises(KeyError, self.sm.getAccessScope, key)
        # Nor a client scope.
        self.assertRaises(KeyError, self.sm.getClientScope, key)

    def test_1003_request_scope_multiple(self):
        file_id = self.sm.addMapping(self.file_mapping)
        folder_id = self.sm.addMapping(self.folder_mapping)
        self.sm.setMappingNameToId('file', file_id)
        self.sm.setMappingNameToId('folder', folder_id)

        key1 = 'request_key1'
        key2 = 'request_key2'
        raw_scope = 'test_scope'
        self.assertFalse(self.sm.requestScope(key1, 'test_scope'))
        # all of them must be valid.
        self.assertFalse(self.sm.requestScope(key1, 
            'http://nohost/plone/scope/file,test_scope'))
        self.assertTrue(self.sm.requestScope(key1, 
            'http://nohost/plone/scope/file,http://nohost/plone/scope/folder'))

        mappings = self.sm.getScope(key1)
        self.assertEqual(len(mappings), 2)
        self.assertTrue(file_id in mappings)
        self.assertTrue(folder_id in mappings)

        self.assertTrue(self.sm.requestScope(key2, 
            'http://nohost/plone/scope/folder'))
        mappings = self.sm.getScope(key2)
        self.assertEqual(len(mappings), 1)
        self.assertTrue(file_id not in mappings)


class CTSMEditingTestCase(unittest.TestCase):
    """
    Testing the profile and management within this scope manager.
    """

    def setUp(self):
        self.sm = ContentTypeScopeManager()
        self.file_profile = ContentTypeScopeProfile()
        self.file_profile.mapping = {'File': ['document_view']}
        self.folder_profile = ContentTypeScopeProfile()
        self.folder_profile.mapping = {'Folder': ['folder_contents']}

    def test_0001_edit(self):
        self.sm.setEditProfile('file', None)
        self.assertRaises(AssertionError, 
            self.sm.setEditProfile, 'file', object())

        self.sm.setEditProfile('file', self.file_profile)
        self.assertEqual(self.sm.getEditProfile('file'), self.file_profile)

    def test_0002_commit_del(self):
        self.sm.setEditProfile('file', self.file_profile)
        self.sm.commitEditProfile('file')
        self.assertEqual(self.sm.getMappingByName('file'),
            self.file_profile.mapping)
        mapping_id = self.sm.getMappingId('file')
        self.assertEqual(self.sm.getMappingMethods(mapping_id),
            ['GET', 'HEAD', 'OPTIONS'])

        self.sm.delMappingName('file')
        self.assertEqual(self.sm.getEditProfile('file'), None)
        self.assertEqual(self.sm.getMappingByName('file', default=None), None)


class CTSMPloneIntegrationTestCase(ptc.PloneTestCase):
    """
    Testing the validation on just the objects with the provided 
    mapping and other Plone integration.
    """

    def afterSetUp(self):
        self.sm = ContentTypeScopeManager()
        self.mapping = {}

    def assertScopeValid(self, accessed, name):
        self.assertTrue(self.sm.validateTargetWithMapping(
            accessed, name, self.mapping))

    def assertScopeInvalid(self, accessed, name):
        self.assertFalse(self.sm.validateTargetWithMapping(
            accessed, name, self.mapping))

    def test_0000_resolve_target(self):
        obj, path = self.sm.resolveTarget(self.folder, 'folder_contents')
        self.assertEqual(obj, 'Folder')
        self.assertEqual(path, 'folder_contents')

    def test_0001_resolve_subtarget(self):
        folder_add = self.folder.restrictedTraverse('+')
        obj, path = self.sm.resolveTarget(folder_add, 'addFolder')
        self.assertEqual(obj, 'Folder')
        self.assertEqual(path, '+/addFolder')

    def test_0002_resolve_nothing(self):
        obj, path = self.sm.resolveTarget(object(), 'addFolder')
        self.assertEqual(obj, None)
        self.assertEqual(path, None)

    def test_0100_root_scope(self):
        self.mapping = {
            'Plone Site': ['folder_contents'],
        }
        self.assertScopeValid(self.portal, 'folder_contents')
        self.assertScopeInvalid(self.portal, 'manage')

    def test_0101_folder_scope(self):
        self.mapping = {
            'Folder': ['folder_contents'],
        }
        self.assertScopeValid(self.folder, 'folder_contents')

    def test_0201_browser_view(self):
        self.mapping = {
            'Folder': ['+/addFile', 'folder_contents'],
        }
        # Adding views.
        folder_add = self.folder.restrictedTraverse('+')
        self.assertScopeValid(folder_add, 'addFile')
        self.assertScopeInvalid(folder_add, 'addFolder')
        self.assertScopeInvalid(self.folder, 'addFile')

        # For whatever reason this happened, but still forbidden by
        # scope restrictions.
        portal_add = self.portal.unrestrictedTraverse('+')
        self.assertScopeInvalid(portal_add, 'addFile')

    def test_0301_asterisk_ending(self):
        self.mapping = {
            'Folder': ['folder*contents', 'test_*'],
            'Plone Site': ['test/test_*', 'test/view*me', 'example/*'],
        }

        self.assertScopeInvalid(self.folder, 'folder_contents')
        self.assertScopeInvalid(self.folder, 'test_view')
        self.assertScopeInvalid(self.folder, 'test_')

        self.assertScopeInvalid(self.portal, 'test_')
        self.assertScopeInvalid(self.portal, 'test/test')
        self.assertScopeInvalid(self.portal, 'test/view_me')
        self.assertScopeValid(self.portal, 'test/test_')
        self.assertScopeValid(self.portal, 'test/test_view')
        self.assertScopeValid(self.portal, 'test/test_page')

        # invalid for now
        self.assertScopeInvalid(self.portal, 'example')
        self.assertScopeValid(self.portal, 'example/')
        self.assertScopeValid(self.portal, 'example/a')


class CTSMValidateTestCase(ptc.PloneTestCase):
    """
    Testing the validation process.
    """

    def afterSetUp(self):
        self.sm = ContentTypeScopeManager()
        self.file_mapping = {'File': ['document_view']}
        self.folder_mapping = {'Folder': ['folder_contents', '+/addFile']}
        file_id = self.sm.addMapping(self.file_mapping)
        folder_id = self.sm.addMapping(self.folder_mapping)
        self.sm.setMappingNameToId('file', file_id)
        self.sm.setMappingNameToId('folder', folder_id)
        self.folder_add = self.folder.restrictedTraverse('+')

        self.all_ids = set([file_id, folder_id])

    def test_0100_request_to_access(self):
        rkey = 'request_key'
        akey = 'access_key'
        self.assertTrue(self.sm.requestScope(rkey, 
            'http://nohost/plone/scope/file,http://nohost/plone/scope/folder'))

        self.sm.setAccessScope(akey, self.sm.getScope(rkey))
        self.assertEqual(self.sm.getAccessScope(akey), self.all_ids)
        # Should there be something to automatically revoke it?
        # Probably?

        request = base.TestRequest()

        self.assertFalse(self.sm.validate(request, '', akey, self.folder,
            self.portal, 'document_view', object()))
        self.assertTrue(self.sm.validate(request, '', akey, self.folder,
            self.portal, 'folder_contents', object()))

        self.assertFalse(self.sm.validate(request, '', akey, self.folder_add,
            self.portal, 'addFolder', object()))
        self.assertTrue(self.sm.validate(request, '', akey, self.folder_add,
            self.portal, 'addFile', object()))

        # TODO test cases where mappings have been purged but the
        # token references to them were not.


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(BTreeScopeManagerTestCase))
    suite.addTest(makeSuite(CTSMMappingTestCase))
    suite.addTest(makeSuite(CTSMEditingTestCase))
    suite.addTest(makeSuite(CTSMPloneIntegrationTestCase))
    suite.addTest(makeSuite(CTSMValidateTestCase))
    return suite
