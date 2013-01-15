import zope.interface
import zope.schema

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.schema import SchemaMethodObject
from pmr2.oauth.utility import buildContentTypeScopeProfileInterface

from pmr2.oauth.interfaces import IContentTypeScopeProfile


class IContentTypeScopeProfileAdd(zope.interface.Interface):
    """
    Fields for the scope profile add form.
    """

    name = zope.schema.ASCIILine(
        title=_(u'Profile Name'),
        description=_(u'The name for the scope profile.'),
        required=True,
    )


class IContentTypeScopeProfileItem(zope.interface.Interface):
    """
    Fields for the scope profile edit form.  This is for the individual
    items.
    """

    name = zope.schema.ASCII(
        title=_(u'Permitted Views'),
        description=_(u'List of views identified by their name that are '
                       'permitted for this content type.'),
        required=False,
    )


class IContentTypeScopeProfileEdit(zope.interface.Interface):
    """
    Interface for editing a scope profile.
    """

    title = zope.schema.TextLine(
        title=_(u'Title'),
        description=_(
            u'Brief description about this scope profile.'),
        required=True,
    )

    description = zope.schema.Text(
        title=_(u'Description'),
        description=_(u'A description of the rights granted by this scope.'),
        required=False,
    )

    methods = zope.schema.ASCIILine(
        title=_(u'Permitted HTTP Methods'),
        description=_(
            u'Whitespace delimited list of permitted HTTP methods for the '
            'subpaths below.'),
        required=True,
        default='GET HEAD OPTIONS',
    )

    mapping = SchemaMethodObject(
        title=_(u'Mapping'),
        description=_(u'A mapping for each of the following portal types to '
                       'a list of permitted subpaths.'),
        schema=buildContentTypeScopeProfileInterface,
        required=False,
    )
