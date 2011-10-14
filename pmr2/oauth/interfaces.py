import zope.interface
import zope.schema

from pmr2.oauth import MessageFactory as _


class BaseInvalidError(KeyError):
    __doc__ = "base invalid error."


class TokenInvalidError(BaseInvalidError):
    __doc__ = "invalid token."


class ConsumerInvalidError(BaseInvalidError):
    __doc__ = "invalid consumer."


class RequestInvalidError(BaseInvalidError):
    __doc__ = "invalid request."


class BaseValueError(ValueError):
    __doc__ = "basic value error"


class CallbackValueError(BaseValueError):
    __doc__ = "callback value error"


class NonceValueError(BaseValueError):
    __doc__ = "nonce value error"


class IOAuthUtility(zope.interface.Interface):
    """\
    The OAuth utility.
    """


class IOAuthPlugin(zope.interface.Interface):
    """\
    The OAuth plugin.
    """

    def extractOAuthCredentials(request):
        """\
        Extract the OAuth credentials from the request, for processing
        by Plone PAS.
        """


class IRequest(zope.interface.Interface):
    """\
    Marker interface for the OAuth request.
    """


class IConsumer(zope.interface.Interface):
    """\
    An OAuth consumer.
    """

    key = zope.schema.ASCIILine(
        title=u'Key',
        description=u'Consumer key',
        required=True,
    )

    secret = zope.schema.ASCIILine(
        title=u'Secret',
        description=u'Consumer secret',
        required=True,
    )


class IConsumerManager(zope.interface.Interface):
    """\
    Consumer utility
    """

    def add(consumer):
        """\
        Add a consumer.
        """

    def check(consumer):
        """\
        Check for validity of input consumer.
        """

    def get(consumer_key, default=None):
        """\
        Return consumer, identified by consumer_key.
        """

    def getValidated(consumer_key, default=None):
        """\
        Return consumer only if it is a validated one.
        """

    def remove(consumer):
        """\
        Remove consumer.
        """


class IScopeManager(zope.interface.Interface):
    """\
    Scope Manager

    A manager that simplifies the handling of scopes, which place limits
    on what an authenticated token can access.
    """

    # individual scope manager should deal with how/what the meaning of
    # the scope value within each token.

    def validate(context, request, scope):
        """\
        Validate the scope against the given context and request.
        """


class IDefaultScopeManager(zope.interface.Interface):
    """\
    Fields for the default scope manager.
    """

    permitted = zope.schema.ASCII(
        title=u'Permitted URIs',
        description=u'List of regular expressions of URIs that are permitted '
                     'to be accessible via OAuth.',
        required=True,
    )


class IToken(zope.interface.Interface):
    """\
    An OAuth token.
    """

    key = zope.schema.ASCIILine(
        title=u'Key',
        description=u'Consumer key',
        required=True,
    )

    secret = zope.schema.ASCIILine(
        title=u'Secret',
        description=u'Consumer secret',
        required=True,
    )

    callback = zope.schema.TextLine(
        title=u'Callback',
        required=True,
    )

    callback_confirmed = zope.schema.ASCIILine(
        title=u'Callback Confirmed',
        required=True,
    )

    verifier = zope.schema.ASCIILine(
        title=u'Verifier',
        required=True,
    )

    # other requirements

    access = zope.schema.Bool(
        title=u'Access Permitted',
        description=u'Determines if this can be used to access content.',
        default=False,
        required=True,
    )

    user = zope.schema.ASCIILine(
        title=u'User ID',
        description=u'The user id associated with this token.',
        required=False,
        default=None,
    )

    consumer_key = zope.schema.ASCIILine(
        title=u'Consumer Key',
        description=u'The consumer key associated with this token',
        required=False,
        default=None,
    )

    timestamp = zope.schema.Int(
        title=u'Timestamp',
        description=u'Creation timestamp of this token',
    )

    scope_id = zope.schema.Text(
        title=u'Scope ID',
        description=u'The id of the scope manager that was used.',
        required=False,
        default=u'',
    )

    scope = zope.schema.Text(
        title=u'Scope',
        description=u'The scope associated with this token, specific to the '
                     'original scope manager that was in use.',
        required=False,
    )


class ITokenManager(zope.interface.Interface):
    """\
    Token manager utility
    """

    def add(token):
        """\
        Add a token.
        """

    def generateRequestToken(consumer, request):
        """\
        Generate a request token, using consumer and request.
        """

    def generateAccessToken(consumer, request):
        """\
        Generate an access token.
        """

    def get(token_key, default=None):
        """\
        Return token, identified by token_key.
        """

    def remove(token):
        """\
        Remove token.
        """


# Other management interfaces

class ICallbackManager(zope.interface.Interface):
    """\
    Callback manager.

    Can be used by token managers to check whether a callback is
    acceptable.
    """

    def check(callback):
        """\
        Check that this callback is valid.
        """


class INonceManager(zope.interface.Interface):
    """\
    Nonce manager.

    If nonce must be checked specifically, implement this manager.
    """

    def check(callback):
        """\
        Check that this nonce can be used.
        """
