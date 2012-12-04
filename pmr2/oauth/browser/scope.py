import zope.component
import zope.interface

from z3c.form import field

from Products.CMFCore.utils import getToolByName

from pmr2.z3cform import form

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import IScopeManager


class ScopeEditForm(form.EditForm):
    """\
    For editing scope.
    """

    @property
    def fields(self):
        sm = self.getContent()
        # this assumes the scope manager implements the immediate 
        # interface and that it provides all the fields for it.
        inf = zope.component.providedBy(sm).interfaces().next()
        return field.Fields(inf)

    def update(self):
        super(ScopeEditForm, self).update()
        self.request['disable_border'] = True

    def getContent(self):
        sm = zope.component.getMultiAdapter(
            (self.context, self.request), IScopeManager)
        return sm

    def getUserTypes(self):
        """
        Return list of types usable by users.
        """

        plone_catalog = getToolByName(self.context, 'plone_catalog')
        plone_utils = getToolByName(self.context, 'plone_utils')
        all_used_types = plone_catalog.uniqueValuesFor('portal_type');
        return plone_utils.getUserFriendlyTypes(all_used_types)
