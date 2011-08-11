import zope.interface
import zope.schema

from pmr2.oauth import MessageFactory as _


class FormValueError(ValueError):
    """\
    Value error generated within forms.
    """


class IOAuthUtility(zope.interface.Interface):
    """\
    The OAuth utility.
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

    user = zope.schema.TextLine(
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

    scope = zope.schema.ASCIILine(
        title=u'Scope',
        description=u'Scope of this token.',
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

    def get(token_key, default=None):
        """\
        Return token, identified by token_key.
        """

    def remove(token):
        """\
        Remove token.
        """
