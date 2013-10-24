import zope.interface
import zope.schema

# XXX exceptions from upstream
from oauthlib.oauth1.rfc5849.errors import OAuth1Error

from pmr2.oauth import MessageFactory as _


class KeyExistsError(KeyError):
    __doc__ = "key exists error"


class BaseInvalidError(KeyError):
    __doc__ = "base invalid error."


class TokenInvalidError(BaseInvalidError):
    __doc__ = "invalid token."


class ConsumerInvalidError(BaseInvalidError):
    __doc__ = "invalid client."


class RequestInvalidError(BaseInvalidError):
    __doc__ = "invalid request."


class BaseValueError(ValueError):
    __doc__ = "basic value error"


class NotRequestTokenError(TokenInvalidError):
    __doc__ = "Not request token"


class NotAccessTokenError(TokenInvalidError):
    __doc__ = "Not access token"


class ExpiredTokenError(TokenInvalidError):
    __doc__ = "Expired token"


class CallbackValueError(BaseValueError):
    __doc__ = "callback value error"


class NonceValueError(BaseValueError):
    __doc__ = "nonce value error"


class InvalidScopeError(BaseValueError):
    __doc__ = "invalid scope."


class IOAuthRequestValidatorAdapter(zope.interface.Interface):
    """
    Interface for the OAuth adapter.
    """

    def __call__():
        """
        Return a boolean value to determine whether access was granted.
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


class IConsumer(zope.interface.Interface):
    """\
    An OAuth client credential.
    """

    key = zope.schema.ASCIILine(
        title=_(u'Client Identifier'),
        description=_(u'The unique identifier for this client'),
        required=True,
    )

    secret = zope.schema.ASCIILine(
        title=_(u'Client Shared-Secret'),
        description=_(u'The secret that is shared between the client and the '
                      'service provider.'),
        required=True,
    )

    title = zope.schema.TextLine(
        title=_(u'Client Name'),
        description=_(u'This is the name of the application that will be '
                      'using this set of client credentials, and serves as '
                      'the identifier that will be presented to resource '
                      'owners during the authorization process.'),
        required=False,
    )

    domain = zope.schema.TextLine(
        title=_(u'Domain Name'),
        description=_(u'If this client is able to receive callbacks, please '
                      'enter its doamin name here as callbacks will be '
                      'validated against this value. Otherwise leave this as ' 
                      'blank.'),
        required=False,
    )

    def validate():
        """
        Self validation.
        """


class IConsumerManager(zope.interface.Interface):
    """\
    Interface for the client management.
    """

    def add(consumer):
        """\
        Add a client.
        """

    def check(consumer):
        """\
        Check for validity of input client.
        """

    def get(consumer_key, default=None):
        """\
        Return client, identified by consumer_key.
        """

    def getAllKeys():
        """\
        Return all client keys tracked by this client manager.
        """

    def getValidated(consumer_key, default=None):
        """\
        Return a client only if it is a validated one.

        This will be used when possible to allow further checks by 
        alternative implementations.
        """

    def remove(consumer):
        """\
        Remove client.
        """


class IScopeManager(zope.interface.Interface):
    """\
    Scope Manager

    A manager that simplifies the handling of scopes, which place limits
    on what an authenticated token can access.
    """

    def setScope(key, scope):
        """
        Set a scope identified by key.
        """

    def getScope(key, scope):
        """
        Get a scope identified by key.
        """

    def popScope(key, scope):
        """
        Pop out a scope identified by key
        """

    def setClientScope(client_key, scope):
        """
        Set the scope provided by client, referenced by client_key.
        """

    def setAccessScope(access_key, scope):
        """
        Set the scope provided by access, referenced by access_key.
        """

    def getClientScope(client_key, default):
        """
        Get the scope for the provided client_key.
        """

    def getAccessScope(access_key, default):
        """
        Get the scope for the provided access_key.
        """

    def delClientScope(client_key):
        """
        Delete the scope for the provided client_key.
        """

    def delAccessScope(access_key):
        """
        Delete the scope for the provided access_key.
        """

    def requestScope(request_key, rawscope):
        """
        Request a scope for the temporary credentials identified by the
        ``request_key``.

        request_key
            the generated request key.
        rawscope
            the raw scope string sent by the client.

        Return True if the rawscope is successfully stored as a scope
        with the request_key, False otherwise.
        
        The actual scope object can be retrieved by calling
        `self.getScope(request_key)` if this was successful.
        """

    def validate(request, client_key, access_key,
            accessed, container, name, value):
        """
        Validate the scope against the given context with the given
        client and owner.

        request
            the request object.

        client_key
            the client (consumer) key.

        access_key
            the access key identifying a given token granted by a
            resource owner.

        accessed
            the immediate object accessed by the client before the
            value

        container
            the real container of the value

        name
            the name used by the client to access the value.

        value
            the value accessed by the client. 

        The latter four fields are normally called by keywords.
        """


class IDefaultScopeManager(IScopeManager):
    """
    Marker interface for the default scope manager.
    """


class IContentTypeScopeManager(IScopeManager):
    """
    A scope manager based on content types.

    A scope manager validates the requested object and the name with a
    content type profile specific to the client and/or resource access
    key if available, or the default profile if not.
    """

    default_mapping_id = zope.schema.Int(
        title=_(u'Default Mapping ID'),
        required=True,
        default=0,
    )

    def resolveProfile(client_key, access_key):
        """
        Reolve the provided client_key and access_key into a validation
        profile.
        """

    def resolveTarget(accessed, name):
        """
        Resolve the accessed item and name into a target for the next
        method.
        """

    def validateTargetWithProfile(accessed_typeid, subpath, profile):
        """
        The scope value will resolve into a profile which is used to
        validate against the provided parameters.
        """


class IContentTypeScopeProfile(zope.interface.Interface):
    """
    Interface for the scope profile and editor.
    """

    title = zope.schema.TextLine(
        title=_(u'Title'),
        description=_(
            u'Brief description about this scope profile.'),
        required=True,
    )

    description = zope.schema.Text(
        title=_(u'Description'),
        description=_(
            u'Detailed description of the rights granted by this scope.'),
        required=False,
    )

    methods = zope.schema.ASCIILine(
        title=_(u'Permitted HTTP Methods'),
        description=_(
            u'Whitespace delimited list of permitted HTTP methods for the '
            'subpaths below.'),
        required=True,
        default='GET HEAD OPTIONS',
    )

    mapping = zope.schema.Dict(
        title=_(u'Mapping'),
        description=_(u'A mapping for each of the following portal types to '
                     'a list of permitted subpaths.'),
        key_type=zope.schema.ASCIILine(
            title=_(u'Portal Type')
        ),
        value_type=zope.schema.List(
            title=_(u'Permitted subpaths'),
            value_type=zope.schema.ASCIILine(title=_(u'Subpath')),
            required=False,
        ),
    )


class IToken(zope.interface.Interface):
    """\
    An OAuth token.
    """

    key = zope.schema.ASCIILine(
        title=_(u'Key'),
        description=_(u'Token key'),
        required=True,
    )

    secret = zope.schema.ASCIILine(
        title=_(u'Secret'),
        description=_(u'Token secret'),
        required=True,
    )

    callback = zope.schema.ASCIILine(
        title=_(u'Callback'),
        required=False,
    )

    verifier = zope.schema.ASCIILine(
        title=_(u'Verifier'),
        required=True,
    )

    # other requirements

    access = zope.schema.Bool(
        title=_(u'Access Permitted'),
        description=_(u'Determines if this can be used to access content.'),
        default=False,
        required=True,
    )

    user = zope.schema.ASCIILine(
        title=_(u'User ID'),
        description=_(u'The user id associated with this token.'),
        required=False,
        default=None,
    )

    consumer_key = zope.schema.ASCIILine(
        title=_(u'Client Key'),
        description=_(u'The client key associated with this token'),
        required=False,
        default=None,
    )

    timestamp = zope.schema.Int(
        title=_(u'Timestamp'),
        description=_(u'Creation timestamp of this token'),
    )

    expiry = zope.schema.Int(
        title=_(u'Expiry'),
        description=_(u'Expiry timestamp for this token'),
    )

    def validate():
        """
        Self validation.
        """


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
        Generate a request token, using client and request.
        """

    def generateAccessToken(consumer, request):
        """\
        Generate an access token.
        """

    def claimRequestToken(token, user):
        """\
        Token claimed by user.
        """

    def get(token, default=None):
        """\
        Get a token by token.

        Input could be a token, or a key.  Returns the same token 
        identified by the key of the input token or the input key.
        """

    def getRequestToken(token, default=False):
        """\
        Return request token identified by token.

        Raises NotRequestTokenError when token is not an access token.
        Raises InvalidTokenError if internal consistency (invariants)
        are violated.
        If token is not found and default value is false, 
        InvalidTokenError should be raised also.
        """

    def getAccessToken(token, default=False):
        """\
        Return access token identified by token.

        Raises NotAccessTokenError when token is not an access token.
        Raises InvalidTokenError if internal consistency (invariants)
        are violated.
        If token is not found and default value is false, 
        InvalidTokenError should be raised also.
        """

    def getTokensForUser(user):
        """\
        Return a list of token keys for a user.
        """

    def remove(token):
        """\
        Remove token.
        """


# Other management interfaces

class ICallbackManager(zope.interface.Interface):
    """
    Callback manager.

    Used to verify the validity of callback URIs.
    """

    def validate(consumer, token):
        """
        Check that the callbacks are valid against both the client and
        the token.  A more thorough implementation should allow multiple
        hosts for clients, matching against the tokens issued, instead
        of just relying on the helper attribute provided by client.

        token
            The token to validate against.
        consumer
            The client to validate against.
        """


class INonceManager(zope.interface.Interface):
    """\
    Nonce manager.

    If nonce must be checked specifically, implement this manager.
    """

    def check(timestamp, nonce):
        """\
        Check that this nonce can be used.
        """


class _IDynamicSchemaInterface(zope.interface.Interface):
    """
    Placeholder
    """
