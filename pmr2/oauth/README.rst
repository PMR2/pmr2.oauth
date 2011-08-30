==============
OAuth for PMR2
==============

This module provides OAuth authentication for PMR2.  Could probably be
used elsewhere in Plone.

Firstly import all the modules we need.
::

    >>> import time
    >>> import urlparse
    >>> import oauth2 as oauth
    >>> import zope.component
    >>> import zope.interface
    >>> from Testing.testbrowser import Browser
    >>> from plone.z3cform.interfaces import IWrappedForm
    >>> from pmr2.oauth.interfaces import *
    >>> from pmr2.oauth.browser import *
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

    >>> browser = Browser()
    >>> browser.open(baseurl + '/test_current_user')
    >>> print browser.contents
    Anonymous User

Trying to view the token authorization page should result in redirection
to login form in a vanilla site.
::

    >>> browser.open(baseurl + '/OAuthAuthorizeToken?oauth_token=test')
    >>> 'credentials_cookie_auth' in browser.url
    True

So we log in, and try again.  The page should render, but the token
provided was invalid so we will receive a token invalid page.
::

    >>> auth_baseurl = baseurl + '/OAuthAuthorizeToken'
    >>> browser.open(baseurl + '/login')
    >>> browser.getControl(name='__ac_name').value = default_user
    >>> browser.getControl(name='__ac_password').value = default_password
    >>> browser.getControl(name='submit').click()
    >>> browser.open(baseurl + '/test_current_user')
    >>> print browser.contents
    test_user_1_
    >>> browser.open(auth_baseurl + '?oauth_token=test')
    >>> 'Invalid Token' in browser.contents
    True
    >>> 'Grant access' in browser.contents
    False
    >>> 'Deny access' in browser.contents
    False

Now we use the token string returned by the token request initiated a
bit earlier.  Two confirmation button should be visible along with the
name of the consumer, along with its identity.
::

    >>> browser.open(auth_baseurl + '?oauth_token=' + token.key)
    >>> 'Grant access' in browser.contents
    True
    >>> 'Deny access' in browser.contents
    True
    >>> 'The site <strong>' + consumer1.key + '</strong>' in browser.contents
    True

We can approve this token by selecting the 'Grant access' button.  Since
no `xoauth_displayname` was specified, the browser should have been
redirected to the callback URL with the token and verifier specified.
::

    >>> browser.getControl(name='form.buttons.approve').click()
    >>> callback_baseurl = baseurl + '/test_oauth_callback?'
    >>> url = browser.url
    >>> url.startswith(callback_baseurl)
    True
    >>> qs = urlparse.parse_qs(urlparse.urlparse(url).query)
    >>> token_verifier = qs['oauth_verifier'][0]
    >>> token_key = qs['oauth_token'][0]
    >>> token.key == token_key
    True

The request token should be updated to include the id of the user that
authorized it.
::

    >>> tokenManager = zope.component.getMultiAdapter(
    ...     (self.portal, request), ITokenManager)
    >>> tokenManager.get(token_key).user
    'test_user_1_'

At this point the verifier should have been assigned by the consumer to
their copy of the same token, but we will defer this till a bit later.


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
    >>> print browser.contents
    test_user_1_
