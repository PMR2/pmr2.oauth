import oauth2

from persistent import Persistent
from persistent.mapping import PersistentMapping

from zope.annotation import factory
import zope.interface
from zope.schema import fieldproperty

from pmr2.oauth.interfaces import IToken
from pmr2.oauth.interfaces import ITokenManager


class TokenManager(PersistentMapping):

    zope.interface.implements(ITokenManager)

TokenManagerFactory = factory(TokenManager)


class Token(Persistent, oauth2.Token):

    zope.interface.implements(IToken)

    key = fieldproperty.FieldProperty(IToken['key'])
    secret = fieldproperty.FieldProperty(IToken['secret'])
    callback = fieldproperty.FieldProperty(IToken['callback'])
    callback_confirmed = fieldproperty.FieldProperty(IToken['callback_confirmed'])
    verifier = fieldproperty.FieldProperty(IToken['verifier'])
    user = fieldproperty.FieldProperty(IToken['user'])
    consumer_key = fieldproperty.FieldProperty(IToken['consumer_key'])
    timestamp = fieldproperty.FieldProperty(IToken['timestamp'])
    scope = fieldproperty.FieldProperty(IToken['scope'])
