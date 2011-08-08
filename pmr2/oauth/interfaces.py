import zope.interface
import zope.schema


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

    # if other attributes are needed to describe a consumer (such as
    # name and description), mix them in from elsewhere.


class IConsumerManager(zope.interface.Interface):
    """\
    Consumer utility
    """

    def add(consumer):
        """\
        Add a consumer.
        """

    def get(consumer_key, default=None):
        """\
        Return consumer, identified by consumer_key.
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

    verifier = zope.schema.TextLine(
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

    consumer_key = zope.schema.TextLine(
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
