import zope.component
from zope.annotation import IAnnotations

from BTrees.OOBTree import OOBTree

from Products.PloneTestCase import ptc

from pmr2.oauth.interfaces import ITokenManager

from pmr2.oauth.tests import base


class MigrationV04TestCase(ptc.PloneTestCase):
    """
    Test case for migration from v0.2 to v0.4
    """

    def afterSetUp(self):
        # old annotation
        ants = IAnnotations(self.portal)
        sm = type('DefaultScopeManager', (object, ),
            {'__module__': 'pmr2.oauth.scope'})
        ants['pmr2.oauth.scope.DefaultScopeManager'] = sm()
        # Might be better to mock this up properly.
        tm = zope.component.getMultiAdapter((self.portal, None), ITokenManager)
        tm._tokens = OOBTree()
        tm._user_token_map = OOBTree()
        tm._tokens.insert('test1', object())
        tm._tokens.insert('test2', object())
        tm._tokens.insert('test3', object())

    def test_0000_migration(self):
        from pmr2.oauth.setuphandlers import scope_upgrade_v0_4
        tm = zope.component.getMultiAdapter((self.portal, None), ITokenManager)
        self.assertEqual(len(tm._tokens), 3)
        scope_upgrade_v0_4(self.portal)
        # 1 for the dummy token.
        self.assertEqual(len(tm._tokens), 1)
        ants = IAnnotations(self.portal)
        self.assertFalse('pmr2.oauth.scope.DefaultScopeManager' in ants)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(MigrationV04TestCase))
    return suite
