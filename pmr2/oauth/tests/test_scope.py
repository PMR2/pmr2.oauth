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
from pmr2.oauth.interfaces import ITokenManager, IConsumerManager
from pmr2.oauth.token import Token
from pmr2.oauth.consumer import Consumer
from pmr2.oauth.scope import BTreeScopeManager, ContentTypeScopeManager

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


class ContentTypeScopeManagerBaseTestCase(ptc.PloneTestCase):
    """
    The base test cases without the handling of client/access keys.
    """

    def afterSetUp(self):
        self.scopeManager = ContentTypeScopeManager()

    def assertScopeValid(self, accessed, name):
        self.assertTrue(self.scopeManager.validate(None, None,
            accessed, None, name, None))

    def assertScopeInvalid(self, accessed, name):
        self.assertFalse(self.scopeManager.validate(None, None,
            accessed, None, name, None))

    def test_0000_empty_scope(self):
        self.assertEqual(self.scopeManager.mappings, None)
        self.assertScopeInvalid(None, '')

    def test_0100_root_scope(self):
        self.scopeManager.mappings = {
            'Plone Site': ['folder_contents'],
        }
        self.assertScopeValid(self.portal, 'folder_contents')
        self.assertScopeInvalid(self.portal, 'manage')

    def test_0101_folder_scope(self):
        self.scopeManager.mappings = {
            'Folder': ['folder_contents'],
        }
        self.assertScopeValid(self.folder, 'folder_contents')

    def test_0201_browser_view(self):
        self.scopeManager.mappings = {
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

    def test_2000_bad_scope_assignment(self):
        self.assertRaises(WrongContainedType, setattr, 
            self.scopeManager, 'mappings', {
                'Folder': 'folder_contents',
            }
        )

        self.assertRaises(WrongType, setattr, 
            self.scopeManager, 'mappings', ['folder_contents']
        )


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(BTreeScopeManagerTestCase))
    suite.addTest(makeSuite(ContentTypeScopeManagerBaseTestCase))
    return suite
