import oauth2 as oauth

from persistent import Persistent
from BTrees.OOBTree import OOBTree

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
import zope.interface
from zope.schema import fieldproperty

from pmr2.oauth.interfaces import IConsumer
from pmr2.oauth.interfaces import IConsumerManager
from pmr2.oauth.factory import factory


class ConsumerManager(Persistent, Contained):
    """\
    A very basic consumer manager for the default layer.

    This manager only capture the very basics, and does not really
    allow users to add their own consumers and have them approved in 
    a way that is more integrated into the Plone (or other) CMS.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)
    zope.interface.implements(IConsumerManager)
    
    def __init__(self):
        self._consumers = OOBTree()

    def add(self, consumer):
        assert IConsumer.providedBy(consumer)
        if self.get(consumer.key):
            raise ValueError('consumer %s already exists', consumer.key)
        self._consumers[consumer.key] = consumer

    def check(self, consumer):
        key = IConsumer.providedBy(consumer) and consumer.key or consumer
        # a very simple check.
        return key in self._consumers.keys()

    def get(self, consumer_key, default=None):
        return self._consumers.get(consumer_key, default)

    def getAllKeys(self):
        return self._consumers.keys()

    def getValidated(self, consumer_key, default=None):
        if self.check(consumer_key):
            return self.get(consumer_key)
        return default

    def remove(self, consumer):
        if IConsumer.providedBy(consumer):
            consumer = consumer.key
        self._consumers.pop(consumer)

ConsumerManagerFactory = factory(ConsumerManager)


class Consumer(Persistent, oauth.Consumer):
    """\
    Basic persistent consumer class.
    """

    zope.interface.implements(IConsumer)

    key = fieldproperty.FieldProperty(IConsumer['key'])
    secret = fieldproperty.FieldProperty(IConsumer['secret'])
