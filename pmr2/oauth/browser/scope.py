import zope.component
import zope.interface

from z3c.form import form
from z3c.form import field

from plone.z3cform.layout import wrap_form

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import *


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

    def getContent(self):
        sm = zope.component.getMultiAdapter(
            (self.context, self.request), IScopeManager)
        return sm

ScopeEditFormView = wrap_form(ScopeEditForm)
