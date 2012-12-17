import new

import zope.interface
from zope.schema import Object

from pmr2.oauth.interfaces import _IDynamicSchemaInterface


class ISchemaMethodObject(zope.interface.Interface):
    pass


class SchemaMethodObject(Object):
    """
    This is a mock object wrapper around a dict to provide just the
    schema interface.
    """

    zope.interface.implements(ISchemaMethodObject)

    @property
    def schema(self):
        # XXX this can be extremely heavy, will need to figure out how
        # to cache this.
        return self._schema()

    def __init__(self, schema, **kw):
        # The schema will be callable instead.
        self._schema = schema
        # Skip the parent validation.
        super(Object, self).__init__(**kw)

    def _validate(self, value):
        super(Object, self)._validate(value)
        # skip the schema validation as value is a dict.


def buildSchemaInterface(fields, schema_factory, schema_keywords=None,
        iname='IDynamicSchemaInterface'
    ):
    """
    Dynamic schema interface builder.
    """

    # Dragons in this method.

    default = {
        '__module__': __name__,
        '__doc__': 'Dynamic schema interface.',
    }

    results = {}
    for c, values in enumerate(sorted(fields)):
        id_, title = values

        kw = {
            'id': id_,
            'title': title,
            'required': False,
        } 

        if schema_keywords:
            kw.update(schema_keywords)

        field = schema_factory(**kw)
        # Specify the order, since the dict is orderless.
        field.order = c
        results[id_] = field
        
    default.update(results)
    
    # Incoming lion, get in the car.
    interfaceClass = new.classobj(iname, (_IDynamicSchemaInterface,), default)
        
    return interfaceClass
