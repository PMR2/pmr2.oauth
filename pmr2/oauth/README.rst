=================
OAuth PAS Plug-in
=================

This module provides OAuth authentication for Plone via the Pluggable
Authentication Service.

To run this, we first import all the modules we need.
::

    >>> import time
    >>> import urlparse
    >>> import oauth2 as oauth
    >>> import zope.component
    >>> import zope.interface
    >>> from Testing.testbrowser import Browser
    >>> from plone.z3cform.interfaces import IWrappedForm
    >>> from pmr2.oauth.interfaces import *
    >>> from pmr2.oauth.browser.token import *
    >>> from pmr2.oauth.consumer import *
    >>> from pmr2.oauth.tests.base import TestRequest
    >>> from pmr2.oauth.tests.base import SignedTestRequest
    >>> request = TestRequest()
    >>> o_logged_view = zope.component.getMultiAdapter(
    ...     (self.portal, request), name='test_current_user')
    >>> baseurl = self.portal.absolute_url()

The default OAuth utility should have been registered.
::

    >>> utility = zope.component.getUtility(IOAuthUtility)
    >>> utility
    <pmr2.oauth.utility.OAuthUtility object at ...>

The request adapter should have been registered.
::

    >>> request = TestRequest()
    >>> zope.component.getAdapter(request, IRequest)
    {}

The default consumer manager should also be available via adapter.
::

    >>> request = TestRequest()
    >>> consumerManager = zope.component.getMultiAdapter(
    ...     (self.portal, request), IConsumerManager)
    >>> consumerManager
    <pmr2.oauth.consumer.ConsumerManager object at ...>

Ditto for the token manager.
::

    >>> request = TestRequest()
    >>> tokenManager = zope.component.getMultiAdapter(
    ...     (self.portal, request), ITokenManager)
    >>> tokenManager
    <pmr2.oauth.token.TokenManager object at ...>

Lastly, the scope manager.
::

    >>> request = TestRequest()
    >>> scopeManager = zope.component.getMultiAdapter(
    ...     (self.portal, request), IScopeManager)
    >>> scopeManager
    <pmr2.oauth.scope.DefaultScopeManager object at ...>


---------------------
Consumer Registration
---------------------

In order for a client to use the site contents, it needs to register
onto the site.  For now we just add a consumer to the ConsumerManager.
::

    >>> consumer1 = Consumer('consumer1.example.com', 'consumer1-secret')
    >>> consumerManager.add(consumer1)
    >>> consumer1 == consumerManager.get('consumer1.example.com')
    True

It will be possible to use the browser form to add one also.


-----------------
Consumer Requests
-----------------

Once the consumer is registered onto the site, it is now possible to
use it to request token.  We can try a standard request without any
authorization, however we should log out here first.
::

    >>> self.logout()
    >>> request = TestRequest()
    >>> rt = RequestTokenPage(self.portal, request)
    >>> rt()
    Traceback (most recent call last):
    ...
    BadRequest: missing oauth parameters

We can try to make up some random request, that should fail because it
is not signed properly.
:::

    >>> timestamp = str(int(time.time()))
    >>> request = TestRequest(oauth_keys={
    ...     'oauth_version': "1.0",
    ...     'oauth_consumer_key': "consumer1.example.com",
    ...     'oauth_nonce': "123123123123123123123123123",
    ...     'oauth_timestamp': timestamp,
    ...     'oauth_callback': "http://www.example.com/oauth/callback",
    ...     'oauth_signature_method': "HMAC-SHA1",
    ...     'oauth_signature': "ANT2FEjwDqxg383D",
    ... })
    >>> rt = RequestTokenPage(self.portal, request)
    >>> rt()
    Traceback (most recent call last):
    ...
    BadRequest: Invalid signature...

Now we construct a request signed with the key, using python-oauth2.
The desired request token string should be generated and returned.
While the callback URL is still on the portal, this is for convenience
sake.
::

    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(oauth_keys={
    ...     'oauth_version': "1.0",
    ...     'oauth_nonce': "4572616e48616d6d65724c61686176",
    ...     'oauth_timestamp': timestamp,
    ...     'oauth_callback': baseurl + '/test_oauth_callback',
    ... }, consumer=consumer1)
    >>> rt = RequestTokenPage(self.portal, request)
    >>> tokenstr = rt()
    >>> print tokenstr
    oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true
    >>> token = oauth.Token.from_string(tokenstr)

Try again using a browser, but try an oob callback.
::

    >>> url = baseurl + '/OAuthRequestToken'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     oauth_keys={
    ...         'oauth_version': "1.0",
    ...         'oauth_nonce': "4572616e48616d6d65724c61686176",
    ...         'oauth_timestamp': timestamp,
    ...         'oauth_callback': 'oob',
    ...     },
    ...     consumer=consumer1, 
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> browser.open(url)
    >>> btokenstr = browser.contents
    >>> print btokenstr
    oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true
    >>> btoken = oauth.Token.from_string(btokenstr)


-------------------
Token Authorization
-------------------

Now the consumer can store this token, and redirect the resource owner
to the authorization page.  Instead of invoking the object directly, we
use the testbrowser to demonstrate the functionality of the 
authentication surrounding this.

Before that though, see if the form itself will render the error message
for an unknown token (we will log our local user back in first).  Also,
we will treat our page as a subform such that the rest of the Plone
templates is not rendered.
::

    >>> class AuthorizeToken(AuthorizeTokenPage):
    ...     zope.interface.implements(IWrappedForm)
    ...
    >>> from Products.PloneTestCase.ptc import portal_owner
    >>> from Products.PloneTestCase.ptc import default_user
    >>> from Products.PloneTestCase.ptc import default_password
    >>> self.login(default_user)
    >>> request = TestRequest(form={
    ...     'oauth_token': 'nope',
    ... })
    ...
    >>> rt = AuthorizeToken(self.portal, request)
    >>> result = rt()
    >>> 'Invalid Token.' in result
    True
    >>> 'type="submit"' in result
    False

Also that the form is rendered for an authorized token.
::

    >>> request = TestRequest(form={
    ...     'oauth_token': token.key,
    ... })
    >>> rt = AuthorizeToken(self.portal, request)
    >>> result = rt()
    >>> 'Invalid Token.' in result
    False
    >>> 'type="submit"' in result
    True

Now we do the test with the test browser class.  First we see that the
browser is currently not logged in.
::

    >>> u_browser = Browser()
    >>> u_browser.open(baseurl + '/test_current_user')
    >>> print u_browser.contents
    Anonymous User

Trying to view the token authorization page should result in redirection
to login form in a vanilla site.
::

    >>> u_browser.open(baseurl + '/OAuthAuthorizeToken?oauth_token=test')
    >>> 'credentials_cookie_auth' in u_browser.url
    True

So we log in, and try again.  The page should render, but the token
provided was invalid so we will receive a token invalid page.
::

    >>> auth_baseurl = baseurl + '/OAuthAuthorizeToken'
    >>> u_browser.open(baseurl + '/login')
    >>> u_browser.getControl(name='__ac_name').value = default_user
    >>> u_browser.getControl(name='__ac_password').value = default_password
    >>> u_browser.getControl(name='submit').click()
    >>> u_browser.open(baseurl + '/test_current_user')
    >>> print u_browser.contents
    test_user_1_
    >>> u_browser.open(auth_baseurl + '?oauth_token=test')
    >>> 'Invalid Token' in u_browser.contents
    True
    >>> 'Grant access' in u_browser.contents
    False
    >>> 'Deny access' in u_browser.contents
    False

Now we use the token string returned by the token request initiated a
bit earlier.  Two confirmation button should be visible along with the
name of the consumer, along with its identity.
::

    >>> u_browser.open(auth_baseurl + '?oauth_token=' + token.key)
    >>> 'Grant access' in u_browser.contents
    True
    >>> 'Deny access' in u_browser.contents
    True
    >>> 'The site <strong>' + consumer1.key + '</strong>' in u_browser.contents
    True

We can approve this token by selecting the 'Grant access' button.  Since
no `xoauth_displayname` was specified, the browser should have been
redirected to the callback URL with the token and verifier specified by
the consumer, such that the consumer can request the access token with 
it.
::

    >>> u_browser.getControl(name='form.buttons.approve').click()
    >>> callback_baseurl = baseurl + '/test_oauth_callback?'
    >>> url = u_browser.url
    >>> url.startswith(callback_baseurl)
    True
    >>> qs = urlparse.parse_qs(urlparse.urlparse(url).query)
    >>> token_verifier = qs['oauth_verifier'][0]
    >>> token_key = qs['oauth_token'][0]
    >>> token.key == token_key
    True

Assuming the redirection was successful, the consumer will now know the
verifier associated with this token, but since we control the consumer
here, we can defer this till a bit later.

On the provider side, the request token should be updated to include the 
id of the user that performed the authorization.
::

    >>> tokenManager.get(token_key).user
    'test_user_1_'

Going to do the same to the second request token with an oob callback.
The difference is, the user will be shown the verification code and will
be asked to supply it to the consumer manually.
::

    >>> u_browser.open(auth_baseurl + '?oauth_token=' + btoken.key)
    >>> u_browser.getControl(name='form.buttons.approve').click()
    >>> u_browser.url.startswith(baseurl)
    True

We are going to extract the token verifier from the token manager and
see that it's in the contents.
::

    >>> tmpToken = tokenManager.get(btoken.key)
    >>> btoken_verifier = tmpToken.verifier
    >>> btoken_verifier in u_browser.contents
    True

Of course the user should have the opportunity to deny the token.  We
can create tokens manually and let the user deny it.  The token would
then be purged, and user will be redirected back to the callback,
which the consumer will then handle this denial.
::

    >>> testtok = tokenManager._generateBaseToken(consumer1, None)
    >>> testtok.callback = baseurl + u'/test_oauth_callback?'
    >>> testtok.set_verifier()
    >>> tokenManager.add(testtok)
    >>> u_browser.open(auth_baseurl + '?oauth_token=' + testtok.key)
    >>> u_browser.getControl(name='form.buttons.deny').click()
    >>> u_browser.url == testtok.get_callback_url()
    True
    >>> tokenManager.get(testtok) is None
    True

In the case of a rejected oob token, a message will be displayed.
::

    >>> testtok = tokenManager._generateBaseToken(consumer1, None)
    >>> testtok.callback = u'oob'
    >>> tokenManager.add(testtok)
    >>> u_browser.open(auth_baseurl + '?oauth_token=' + testtok.key)
    >>> u_browser.getControl(name='form.buttons.deny').click()
    >>> u_browser.url.startswith(baseurl)
    True
    >>> 'Token has been denied.' in u_browser.contents
    True
    >>> tokenManager.get(testtok) is None
    True


----------------------------
Request the Authorized Token
----------------------------

As the consumer had received the verifier from the resource owner in the
previous step, construction of the final request to acquire the
authorized token can proceed.

Trying to request an access token without a supplying a valid token will
get you this (log back out first).
::

    >>> self.logout()
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(oauth_keys={
    ...     'oauth_version': "1.0",
    ...     'oauth_nonce': "806052fe5585b22f63fe27cba8b78732",
    ...     'oauth_timestamp': timestamp,
    ... }, consumer=consumer1)
    >>> rt = GetAccessTokenPage(self.portal, request)
    >>> result = rt()
    Traceback (most recent call last):
    ...
    BadRequest: invalid token

Now for the token, but let's try to request an access token without the
correct verifier assigned.
::

    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(oauth_keys={
    ...     'oauth_version': "1.0",
    ...     'oauth_nonce': "806052fe5585b22f63fe27cba8b78732",
    ...     'oauth_timestamp': timestamp,
    ... }, consumer=consumer1, token=token)
    >>> rt = GetAccessTokenPage(self.portal, request)
    >>> print rt()
    Traceback (most recent call last):
    ...
    BadRequest: invalid token

Okay, now do this properly with the verifier provided, as the consumer
just accessed the callback URL of the consumer to supply it with the
correct verifier.
::

    >>> token.verifier = token_verifier
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(oauth_keys={
    ...     'oauth_version': "1.0",
    ...     'oauth_nonce': "806052fe5585b22f63fe27cba8b78732",
    ...     'oauth_timestamp': timestamp,
    ... }, consumer=consumer1, token=token)
    >>> rt = GetAccessTokenPage(self.portal, request)
    >>> accesstokenstr = rt()
    >>> print accesstokenstr
    oauth_token_secret=...&oauth_token=...
    >>> access_token = oauth.Token.from_string(accesstokenstr)

After verification, the old token should have been discarded and cannot
be used again to request a new token.
::

    >>> token.verifier = token_verifier
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(oauth_keys={
    ...     'oauth_version': "1.0",
    ...     'oauth_nonce': "806052fe5585b22f63fe27cba8b78732",
    ...     'oauth_timestamp': timestamp,
    ... }, consumer=consumer1, token=token)
    >>> rt = GetAccessTokenPage(self.portal, request)
    >>> rt()
    Traceback (most recent call last):
    ...
    BadRequest: invalid token

Now try again using the browser.
::

    >>> url = baseurl + '/OAuthGetAccessToken'
    >>> btoken.verifier = btoken_verifier
    >>> request = SignedTestRequest(consumer=consumer1, token=btoken, url=url)
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> browser.open(url)
    >>> baccesstokenstr = browser.contents
    >>> print baccesstokenstr
    oauth_token_secret=...&oauth_token=...
    >>> bacctoken = oauth.Token.from_string(baccesstokenstr)


------------------
Using OAuth Tokens
------------------

This is basic auth, which we want to avoid since consumers would have to
retain (thus know) the user/password combination.
::

    >>> baseurl = self.portal.absolute_url()
    >>> browser = Browser()
    >>> auth = '%s:%s' % (default_user, default_password)
    >>> browser.addHeader('Authorization', 'Basic %s' % auth.encode('base64'))
    >>> browser.open(baseurl + '/test_current_user')
    >>> print browser.contents
    test_user_1_

For the OAuth testing request, we need to generate the authorization
header proper, so we instantiate a signed request object and use it to
build this string.
::

    >>> url = baseurl + '/test_current_user'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     oauth_keys={
    ...         'oauth_version': "1.0",
    ...         'oauth_nonce': "806052fe5585b22f63fe27cba8b78732",
    ...         'oauth_timestamp': timestamp,
    ...     },
    ...     consumer=consumer1, 
    ...     token=access_token, 
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> browser.open(url)
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 403: Forbidden

There is one more security consideration that needs to be satisified
still - the scope.  The default scope manager only permit GET requests,
and they must match one of the permit rules that it contains.  Add this
URL and try again.
::

    >>> scopeManager.permitted = 'test_current_user$\ntest_current_roles$\n'
    >>> browser.open(url)
    >>> print browser.contents
    test_user_1_

Try the roles view also, since it is also permitted.
::

    >>> url = baseurl + '/test_current_roles'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     oauth_keys={
    ...         'oauth_version': "1.0",
    ...         'oauth_nonce': "806052fe5585b22f63fe27cba8b78732",
    ...         'oauth_timestamp': timestamp,
    ...     },
    ...     consumer=consumer1, 
    ...     token=access_token, 
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> browser.open(url)
    >>> print browser.contents
    Member
    Authenticated


-----
Scope
-----

While the current scope manager already place limits on what consumers
can access, individual users should be able to place further
restrictions on the amount of their resources a given consumer may
access.  Attaching a scope to a token is a method that enables this 
limitation.  As the implementation is completely extensible, the
specific parameters used/accepted by the scope is dependent on those 
details, likewise for the presentation of the scope to the end user
(e.g. implementation of scope managers can translate raw scope into
icons of a provided service more easily identifiable to end users).

For our demonstration, we continue our usage of the default scope
manager by specifying a regular expression matching a URI.  Here we have
a consumer requesting a token like earlier, but with a scope parameter
defined.
::

    >>> url = baseurl + '/OAuthRequestToken?scope=test_current_user%24'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     oauth_keys={
    ...         'oauth_version': "1.0",
    ...         'oauth_nonce': "109850980381481596938563",
    ...         'oauth_timestamp': timestamp,
    ...         'oauth_callback': baseurl + '/test_oauth_callback',
    ...     },
    ...     consumer=consumer1,
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> consumer_browser = Browser()
    >>> consumer_browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> consumer_browser.open(url)
    >>> scoped_request_tokenstr = consumer_browser.contents
    >>> print scoped_request_tokenstr
    oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true
    >>> scoped_request_token = oauth.Token.from_string(scoped_request_tokenstr)

Verify that our scope value is stored in the request token.
::

    >>> srt_key = scoped_request_token.key
    >>> raw_srt = tokenManager.get(srt_key)
    >>> print raw_srt.scope
    test_current_user$

Much like before, the user would be directed to the authorization page,
this time the specific scope this consumer would like to access is
visible.  We also reuse the original current user's browser (which
should still be logged in).  Also, since this token is limited in scope,
the user should be informed.
::

    >>> u_browser.open(auth_baseurl + '?oauth_token=' + srt_key)
    >>> 'The site <strong>' + consumer1.key + '</strong>' in u_browser.contents
    True
    >>> 'test_current_user$' in u_browser.contents
    True

User is nice once more and authorizes this second token.
::

    >>> u_browser.getControl(name='form.buttons.approve').click()
    >>> url = u_browser.url
    >>> qs = urlparse.parse_qs(urlparse.urlparse(url).query)
    >>> token_verifier = qs['oauth_verifier'][0]
    >>> scoped_request_token.verifier = token_verifier

Complete the authorization by requesting the access token, and see that
it retains the scope that was specified in the request token.
::

    >>> url = baseurl + '/OAuthGetAccessToken'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     oauth_keys={
    ...         'oauth_version': "1.0",
    ...         'oauth_nonce': "028516734893275926641849",
    ...         'oauth_timestamp': timestamp,
    ...     }, 
    ...     consumer=consumer1, 
    ...     token=scoped_request_token,
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> consumer_browser = Browser()
    >>> consumer_browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> consumer_browser.open(url)
    >>> scoped_access_tokenstr = consumer_browser.contents
    >>> print scoped_access_tokenstr
    oauth_token_secret=...&oauth_token=...
    >>> scoped_access_token = oauth.Token.from_string(scoped_access_tokenstr)
    >>> sat_key = scoped_access_token.key
    >>> raw_sat = tokenManager.get(sat_key)
    >>> print raw_sat.scope
    test_current_user$

With this token, consumer only requested the current user and not the
roles view, so this request should result in a forbidden error (even
though it is publicly visible).
::

    >>> url = baseurl + '/test_current_roles'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     oauth_keys={
    ...         'oauth_version': "1.0",
    ...         'oauth_nonce': "028516734893275926641849",
    ...         'oauth_timestamp': timestamp,
    ...     }, 
    ...     consumer=consumer1, 
    ...     token=scoped_access_token,
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> consumer_browser = Browser()
    >>> consumer_browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> consumer_browser.open(url)
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 403: Forbidden

Now attempt to use it to access a permitted resource, in this case it
would be the test_current_user view.
::

    >>> url = baseurl + '/test_current_user'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     oauth_keys={
    ...         'oauth_version': "1.0",
    ...         'oauth_nonce': "028516734893275926641849",
    ...         'oauth_timestamp': timestamp,
    ...     }, 
    ...     consumer=consumer1, 
    ...     token=scoped_access_token,
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> consumer_browser = Browser()
    >>> consumer_browser.addHeader('Authorization', 'OAuth %s' % auth)
    >>> consumer_browser.open(url)
    >>> print consumer_browser.contents
    test_user_1_

However, if this view is no longer permitted by the default scope
manager, it should no longer be accessible.
::

    >>> scopeManager.permitted = 'test_current_roles$\n'
    >>> consumer_browser.open(url)
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 403: Forbidden


---------------------
Management Interfaces
---------------------

Finally, the user (and site managers) would need to know what tokens are
stored for who and also the ability to revoke tokens when they no longer
wish to retain access for the consumer.  This is where the management
form comes in.

Do note that as of this release, the URIs to the following management
interfaces are not linked.  Site administrators may wish to add them
manually if they wish to make these functions more visible.

As our test user have granted access to two tokens already, they both
should show up if the listing page is viewed.
::

    >>> from pmr2.oauth.browser import user
    >>> self.login(default_user)
    >>> request = TestRequest()
    >>> view = user.UserTokenForm(self.portal, request)
    >>> result = view()
    >>> access_token.key in result
    True
    >>> scoped_access_token.key in result
    True
    >>> 'consumer1.example.com' in result
    True

All the required data are present in the form.  Let's try to remove one
of the tokens using the test browser.
::

    >>> u_browser.open(baseurl + '/issued_oauth_tokens')
    >>> u_browser.getControl(name="form.widgets.key").controls[0].click()
    >>> u_browser.getControl(name='form.buttons.revoke').click()
    >>> len(tokenManager.getTokensForUser(default_user))
    2
    >>> result = u_browser.contents
    >>> 'Access successfully removed' in result
    True

Same deal for consumers, we can open the consumer management form and
we should see the single consumer that had been added earlier.  Site
managers can access this page at `${portal_url}/manage-oauth-consumers`.
::

    >>> from pmr2.oauth.browser import consumer
    >>> request = TestRequest()
    >>> view = consumer.ConsumerManageForm(self.portal, request)
    >>> zope.interface.directlyProvides(view, IWrappedForm)
    >>> result = view()
    >>> 'consumer1.example.com' in result
    True

We can try to add a few consumers using the form also.
::

    >>> request = TestRequest(form={
    ...     'form.widgets.key': 'consumer2.example.com',
    ...     'form.buttons.add': 1,
    ... })
    >>> view = consumer.ConsumerAddForm(self.portal, request)
    >>> view.update()

    >>> request = TestRequest(form={
    ...     'form.widgets.key': 'consumer3.example.com',
    ...     'form.buttons.add': 1,
    ... })
    >>> view = consumer.ConsumerAddForm(self.portal, request)
    >>> view.update()

Now the management form should show these couple new consumers.
::

    >>> request = TestRequest()
    >>> view = consumer.ConsumerManageForm(self.portal, request)
    >>> result = view()
    >>> 'consumer2.example.com' in result
    True
    >>> 'consumer3.example.com' in result
    True

Should have no problems removing them either.
::

    >>> request = TestRequest(form={
    ...     'form.widgets.key': [
    ...         'consumer2.example.com', 'consumer3.example.com'],
    ...     'form.buttons.remove': 1,
    ... })
    >>> view = consumer.ConsumerManageForm(self.portal, request)
    >>> result = view()
    >>> 'consumer2.example.com' in result
    False
    >>> 'consumer3.example.com' in result
    False

Lastly, scope manager also has a simple form that allow basic editing of
global scope parameters for the current active scope manager.  The URI
to this is `${portal_url}/manage-oauth-consumers`.
::

    >>> from pmr2.oauth.browser import scope
    >>> request = TestRequest()
    >>> view = scope.ScopeEditForm(self.portal, request)
    >>> zope.interface.directlyProvides(view, IWrappedForm)
    >>> result = view()
    >>> 'test_current_roles$' in result
    True

That value can be edited.
::

    >>> request = TestRequest(form={
    ...     'form.widgets.permitted': 'test_current_user$',
    ...     'form.buttons.apply': 1,
    ... })
    >>> view = scope.ScopeEditForm(self.portal, request)
    >>> zope.interface.directlyProvides(view, IWrappedForm)
    >>> result = view()
    >>> 'test_current_roles$' in result
    False
    >>> 'test_current_user$' in result
    True
