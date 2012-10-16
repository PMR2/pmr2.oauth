import zope.component
import zope.interface
from zope.publisher.browser import BrowserPage

from z3c.form import form
from z3c.form import field
from z3c.form import button

from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import *
from pmr2.oauth.browser.template import ViewPageTemplateFile
from pmr2.oauth.browser.template import path
from pmr2.oauth.browser.form import Form
from pmr2.oauth.utility import random_string

from pmr2.oauth.consumer import Consumer


class ConsumerAddForm(form.AddForm):
    """\
    For adding consumers
    """

    fields = field.Fields(IConsumer).select(
        'key',
        # secret should be generated.
    )

    def update(self):
        super(ConsumerAddForm, self).update()
        self.request['disable_border'] = True

    def create(self, data):
        # I don't think we need a consumer factory for this... just
        # inherit/redefine this form for your consumers.
        return Consumer(data['key'], random_string(24))

    def add(self, object):
        cm = zope.component.getMultiAdapter(
            (self.context, self.request), IConsumerManager)
        cm.add(object)

    def nextURL(self):
        return self.context.absolute_url() + '/manage-oauth-consumers'


class ConsumerManageForm(Form):
    """\
    For user to manage their authorized tokens.
    """

    ignoreContext = True
    template = ViewPageTemplateFile(path('consumer_manage_token.pt'))

    def getConsumers(self):
        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)
        keys = cm.getAllKeys()

        # TODO rather than listing all secrets with this form, make it
        # so it will be possible to review the keys on a per-consumer
        # basis along with any fields specific to one.

        consumers = [cm.get(k) for k in keys]
        return consumers

    def update(self):
        super(ConsumerManageForm, self).update()
        self.consumers = self.getConsumers()
        self.request['disable_border'] = True

    @button.buttonAndHandler(_('Remove'), name='remove')
    def handleRemove(self, action):
        """\
        User revokes selected consumers.
        """

        # manually do everything since we are not using the built-in
        # widgets
        # TODO use widgets?
        # removing consumers does not remove corresponding tokens that 
        # were issued previous to this, although the tokens will cease
        # to work without the corresponding secret.

        removed = error = 0
        keys = self.request.form.get('form.widgets.key', [])
        if isinstance(keys, basestring):
            # don't cast a string into a list as we are expecting one.
            keys = [keys]
        
        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)
        for k in keys:
            try:
                cm.remove(k)
                removed += 1
            except:
                error = 1

        status = IStatusMessage(self.request)
        if error:
            status.addStatusMessage(
                _(u'Errors encountered during key removal'),
                type="error")
        if removed:
            status.addStatusMessage(
                _(u'Consumers successfully removed'),
                type="info")
