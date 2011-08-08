import oauth2 as oauth
import zope.interface

import Acquisition

from pmr2.oauth.interfaces import IConsumer
from pmr2.oauth.interfaces import IConsumerManager
from pmr2.oauth.tests.base import TestRequest


class MockPAS(Acquisition.Implicit):
    def __init__(self):
        self.REQUEST = TestRequest()


class MockSite(Acquisition.Implicit):

    def absolute_url(self):
        return "http://nohost/"


class MockConsumerManager(dict):

    zope.interface.implements(IConsumerManager)

    def add(self, consumer):
        self[consumer.key] = consumer.secret

    def get(self, key, default=None):
        if key in self:
            return MockConsumer(key, self[key])
        else:
            raise KeyError

    def remove(self, consumer):
        # remove consumer identified by key `consumer`
        if self.get(consumer):
            return self.pop(consumer)


class MockConsumer(oauth.Consumer):

    zope.interface.implements(IConsumer)
