from z3c.form import form

from plone.app.z3cform.interfaces import IPloneFormLayer

from pmr2.oauth.browser.template import path, ViewPageTemplateFile


class Form(form.Form):

    index = ViewPageTemplateFile(path('wrapped_form.pt'))

    def renderContents(self):
        return super(Form, self).render()

    def render(self):
        self.contents = self.renderContents()

        if (not IPloneFormLayer.providedBy(self.request) or 
                self.template is None):
            # The default cases.
            return self.contents

        # Template is overriden and plone form layer is active.
        if self.request.response.getStatus() in (302, 303):
            return u""

        return self.index()
