import zope.component

from z3c.form.interfaces import IObjectWidget
from z3c.form.object import ObjectConverter

from pmr2.oauth.schema import ISchemaMethodObject


class SchemaMethodObjectConverter(ObjectConverter):
    """
    Data converter for the dynamic schema object that's really a 
    wrapper for a dict.
    """

    zope.component.adapts(ISchemaMethodObject, IObjectWidget)

    def toFieldValue(self, value):
        # The value provided is a dict, and this isn't an for an object
        # but borrows whatever useful from the object related classes to
        # hammer the desired value into the source dict, so the value is
        # already what is needed.
        return value


def NullConverter(obj):
    """
    Does not actually convert anything, just tell the adapter to reuse
    the object.
    """

    return obj
