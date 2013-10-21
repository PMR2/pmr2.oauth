import time
import unittest

from zope.component import provideAdapter
from zope.schema import Object
from zope.interface import Interface
from zope.interface import implementer

from z3c.form.interfaces import NO_VALUE
from z3c.form.field import Fields
from z3c.form.object import ObjectWidget
from z3c.form.datamanager import DictionaryField

from pmr2.oauth.schema import CTSMMappingList
from pmr2.oauth.schema import SchemaMethodObject
from pmr2.oauth.converter import SchemaMethodObjectConverter


class ITest(Interface):
    items = CTSMMappingList(title=u"Test")

@implementer(ITest)
class Test(object):
    pass


class ConverterTestCase(unittest.TestCase):

    def setUp(self):
        # Ensure that the dictionaries we passing in for the tests can
        # be understood as conversion sources.
        provideAdapter(DictionaryField)

        self.dummy = Test()
        self.field = Object(ITest)
        self.widget = ObjectWidget(self.dummy)

    def tearDown(self):
        pass

    def test_base_convert(self):
        converter = SchemaMethodObjectConverter(self.field, self.widget)
        self.assertEqual(converter.toWidgetValue(None), NO_VALUE)
        self.assertEqual(converter.toWidgetValue({'items': None}),
            {'items': None})

    def test_convert_null(self):
        converter = SchemaMethodObjectConverter(self.field, self.widget)
        # Undefined list items must NOT return NO_VALUE as that token
        # will not recognized as None and then some place else will try
        # to iterate through it.
        self.assertEqual(converter.toWidgetValue({}), {'items': None})


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ConverterTestCase))
    return suite
