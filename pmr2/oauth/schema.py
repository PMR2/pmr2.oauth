import new

import zope.interface
from zope.schema import Object, List
from zope.schema.interfaces import IList, ISequence

from pmr2.oauth.interfaces import _IDynamicSchemaInterface


class ICTSMMappingList(IList):
    pass


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


class CTSMMappingList(List):
    """
    Customized List schema to prevent accidental overriding.
    """

    zope.interface.implements(ICTSMMappingList)


def buildSchemaInterface(fields, schema_factory, schema_keywords=None,
        iname='IDynamicSchemaInterface', sort=True,
    ):
    """
    Dynamic schema interface builder.
    """

    # Dragons in this method.

    default = {
        '__module__': __name__,
        '__doc__': 'Dynamic schema interface.',
    }

    items = enumerate(fields)
    if sort:
        # maybe check whether sort is callable, if so, use it as the
        # sort method.
        items = enumerate(sorted(fields))

    results = {}
    for c, values in items:
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
