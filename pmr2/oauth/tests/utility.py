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
