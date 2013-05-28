from persistent import Persistent
from BTrees.OOBTree import OOBTree

from zope.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
import zope.interface
from zope.schema import fieldproperty

from pmr2.oauth.interfaces import IConsumer
from pmr2.oauth.interfaces import IConsumerManager
from pmr2.oauth.factory import factory
from pmr2.oauth.utility import random_string


class ConsumerManager(Persistent, Contained):
    """\
    A very basic consumer manager for the default layer.

    This manager only capture the very basics, and does not really
    allow users to add their own consumers and have them approved in 
    a way that is more integrated into the Plone (or other) CMS.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)
    zope.interface.implements(IConsumerManager)

    __dummy_key = fieldproperty.FieldProperty(IConsumer['key'])
    __dummy_secret = fieldproperty.FieldProperty(IConsumer['secret'])

    @property
    def DUMMY_KEY(self):
        return self.__dummy_key

    @property
    def DUMMY_SECRET(self):
        return self.__dummy_secret
    
    def __init__(self):
        self.__dummy_key = random_string(24)
        self.__dummy_secret = random_string(24)
        self._consumers = OOBTree()

    def add(self, consumer):
        assert IConsumer.providedBy(consumer)
        if self.get(consumer.key):
            raise ValueError('consumer %s already exists', consumer.key)
        self._consumers[consumer.key] = consumer

    def get(self, consumer_key, default=None):
        return self._consumers.get(consumer_key, default)

    def getValidated(self, consumer_key, default=None):
        # Provision for further checks by alternative implementations.
        return self.get(consumer_key, default)

    def getAllKeys(self):
        return self._consumers.keys()

    def makeDummy(self):
        return Consumer(str(self.DUMMY_KEY), str(self.DUMMY_SECRET))

    def remove(self, consumer):
        if IConsumer.providedBy(consumer):
            consumer = consumer.key
        self._consumers.pop(consumer)

ConsumerManagerFactory = factory(ConsumerManager)


class Consumer(Persistent):
    """\
    Basic persistent consumer class.
    """

    zope.interface.implements(IConsumer)

    key = fieldproperty.FieldProperty(IConsumer['key'])
    secret = fieldproperty.FieldProperty(IConsumer['secret'])
    title = fieldproperty.FieldProperty(IConsumer['title'])
    domain = fieldproperty.FieldProperty(IConsumer['domain'])

    def __init__(self, key, secret, title=None, domain=None):
        assert not ((key is None) or (secret is None))
        self.key = key
        self.secret = secret
        self.title = title
        self.domain = domain

    def __eq__(self, other):
        same_type = isinstance(other, self.__class__)
        return (same_type and 
            self.key == other.key and self.secret == other.secret)

    def validate(self):
        return True
