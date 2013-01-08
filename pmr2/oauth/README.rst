=================
OAuth PAS Plug-in
=================

This module provides OAuth authentication for Plone via the Pluggable
Authentication Service.

To run this, we first import all the modules we need::

    >>> import time
    >>> import urlparse
    >>> import zope.component
    >>> import zope.interface
    >>> from Testing.testbrowser import Browser
    >>> from Products.statusmessages.interfaces import IStatusMessage
    >>> from pmr2.oauth.interfaces import *
    >>> from pmr2.oauth.consumer import *
    >>> from pmr2.oauth.tests.base import makeToken
    >>> from pmr2.oauth.tests.base import TestRequest
    >>> from pmr2.oauth.tests.base import SignedTestRequest
    >>> request = TestRequest()
    >>> o_logged_view = zope.component.getMultiAdapter(
    ...     (self.portal, request), name='test_current_user')
    >>> baseurl = self.portal.absolute_url()

The OAuth adapter should have been set up::

    >>> request = TestRequest()
    >>> oauthAdapter = zope.component.getMultiAdapter(
    ...     (self.portal, request), IOAuthAdapter)
    >>> oauthAdapter
    <pmr2.oauth.utility.SiteRequestOAuth1ServerAdapter object at ...>

The default consumer manager should also be available via adapter::

    >>> request = TestRequest()
    >>> consumerManager = zope.component.getMultiAdapter(
    ...     (self.portal, request), IConsumerManager)
    >>> consumerManager
    <pmr2.oauth.consumer.ConsumerManager object at ...>

Ditto for the token manager::

    >>> request = TestRequest()
    >>> tokenManager = zope.component.getMultiAdapter(
    ...     (self.portal, request), ITokenManager)
    >>> tokenManager
    <pmr2.oauth.token.TokenManager object at ...>

Lastly, the scope manager.  Verify that this component is registered for
both the base generic interface and its specific interface::

    >>> request = TestRequest()
    >>> scopeManager = zope.component.getMultiAdapter(
    ...     (self.portal, request), IScopeManager)
    >>> scopeManager
    <pmr2.oauth.scope.ContentTypeScopeManager object at ...>
    >>> IScopeManager.providedBy(scopeManager)
    True
    >>> result = zope.component.getMultiAdapter(
    ...     (self.portal, request), IContentTypeScopeManager)
    >>> scopeManager == result
    True


---------------------
Consumer Registration
---------------------

In order for a client to use the site contents, it needs to register
onto the site.  For now we just add a consumer to the ConsumerManager::

    >>> consumer1 = Consumer('consumer1.example.com', 'consumer1-secret')
    >>> consumer1.title = u'consumer1.example.com'
    >>> consumerManager.add(consumer1)
    >>> consumer1 == consumerManager.get('consumer1.example.com')
    True

It will be possible to use the browser form to add one also.


-----------------
Consumer Requests
-----------------

Once the consumer is registered onto the site, it is now possible to
use it to request token.  We can try a standard request without any
authorization, however we should log out here first::

    >>> from pmr2.oauth.browser import token
    >>> self.logout()
    >>> request = TestRequest()
    >>> rt = token.RequestTokenPage(self.portal, request)
    >>> rt()
    Traceback (most recent call last):
    ...
    BadRequest...

Now we construct a request signed with the key.  The desired request 
token string should be generated and returned.  While the callback URL 
is still on the portal, this is for convenience sake::

    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     timestamp=timestamp,
    ...     consumer=consumer1,
    ...     callback=baseurl + '/test_oauth_callback',
    ... )
    >>> rt = token.RequestTokenPage(self.portal, request)
    >>> atokenstr = rt()
    >>> print atokenstr
    oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true
    >>> atoken = makeToken(atokenstr)

Try again using a browser, but try an oob callback::

    >>> url = baseurl + '/OAuthRequestToken'
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     consumer=consumer1, 
    ...     url=url,
    ...     callback='oob',
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> btokenstr = browser.contents
    >>> print btokenstr
    oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true
    >>> btoken = makeToken(btokenstr)


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
templates is not rendered::

    >>> from Products.PloneTestCase.ptc import portal_owner
    >>> from Products.PloneTestCase.ptc import default_user
    >>> from Products.PloneTestCase.ptc import default_password
    >>> self.login(default_user)
    >>> request = TestRequest(form={
    ...     'oauth_token': 'nope',
    ... })
    ...
    >>> rt = token.AuthorizeTokenForm(self.portal, request)
    >>> result = rt()
    >>> 'Invalid Token.' in result
    True
    >>> 'type="submit"' in result
    False

Also that the form is rendered for an authorized token::

    >>> request = TestRequest(form={
    ...     'oauth_token': atoken.key,
    ... })
    >>> rt = token.AuthorizeTokenForm(self.portal, request)
    >>> result = rt()
    >>> 'Invalid Token.' in result
    False
    >>> 'type="submit"' in result
    True

Now we do the test with the test browser class.  First we see that the
browser is currently not logged in::

    >>> u_browser = Browser()
    >>> u_browser.open(baseurl + '/test_current_user')
    >>> print u_browser.contents
    Anonymous User

Trying to view the token authorization page should result in redirection
to login form in a vanilla site::

    >>> u_browser.open(baseurl + '/OAuthAuthorizeToken?oauth_token=test')
    >>> 'credentials_cookie_auth' in u_browser.url
    True

So we log in, and try again.  The page should render, but the token
provided was invalid so we will receive a token invalid page::

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
name of the consumer, along with its identity::

    >>> u_browser.open(auth_baseurl + '?oauth_token=' + atoken.key)
    >>> 'Grant access' in u_browser.contents
    True
    >>> 'Deny access' in u_browser.contents
    True
    >>> '<strong>consumer1.example.com</strong>' in u_browser.contents
    True

We can approve this token by selecting the 'Grant access' button.  Since
no `xoauth_displayname` was specified, the browser should have been
redirected to the callback URL with the token and verifier specified by
the consumer, such that the consumer can request the access token with 
it::

    >>> u_browser.getControl(name='form.buttons.approve').click()
    >>> callback_baseurl = baseurl + '/test_oauth_callback?'
    >>> url = u_browser.url
    >>> url.startswith(callback_baseurl)
    True
    >>> qs = urlparse.parse_qs(urlparse.urlparse(url).query)
    >>> atoken_verifier = qs['oauth_verifier'][0]
    >>> atoken_key = qs['oauth_token'][0]
    >>> atoken.key == atoken_key
    True

Assuming the redirection was successful, the consumer will now know the
verifier associated with this token, but since we control the consumer
here, we can defer this till a bit later.

On the provider side, the request token should be updated to include the 
id of the user that performed the authorization::

    >>> tokenManager.get(atoken_key).user
    'test_user_1_'

Going to do the same to the second request token with an oob callback.
The difference is, the user will be shown the verification code and will
be asked to supply it to the consumer manually::

    >>> u_browser.open(auth_baseurl + '?oauth_token=' + btoken.key)
    >>> u_browser.getControl(name='form.buttons.approve').click()
    >>> u_browser.url.startswith(baseurl)
    True

We are going to extract the token verifier from the token manager and
see that it's in the contents::

    >>> tmpToken = tokenManager.get(btoken.key)
    >>> btoken_verifier = tmpToken.verifier
    >>> btoken_verifier in u_browser.contents
    True

Of course the user should have the opportunity to deny the token.  We
can create tokens manually and let the user deny it.  The token would
then be purged, and user will be redirected back to the callback,
which the consumer will then handle this denial::

    >>> testtok = tokenManager.generateRequestToken(consumer1.key,
    ...     baseurl + '/test_oauth_callback?')
    >>> scopeManager.requestScope(testtok.key, None)
    True
    >>> u_browser.open(auth_baseurl + '?oauth_token=' + testtok.key)
    >>> u_browser.getControl(name='form.buttons.deny').click()
    >>> u_browser.url == testtok.get_callback_url()
    True
    >>> tokenManager.get(testtok) is None
    True
    >>> scopeManager.getScope(testtok.key, None) is None
    True

In the case of a rejected oob token, a message will be displayed::

    >>> testtok = tokenManager.generateRequestToken(consumer1.key, 'oob')
    >>> scopeManager.requestScope(testtok.key, None)
    True
    >>> u_browser.open(auth_baseurl + '?oauth_token=' + testtok.key)
    >>> u_browser.getControl(name='form.buttons.deny').click()
    >>> u_browser.url.startswith(baseurl)
    True
    >>> 'Token has been denied.' in u_browser.contents
    True
    >>> tokenManager.get(testtok) is None
    True
    >>> scopeManager.getScope(testtok.key, None) is None
    True


----------------------------
Request the Authorized Token
----------------------------

As the consumer had received the verifier from the resource owner in the
previous step, construction of the final request to acquire the
authorized token can proceed.

Trying to request an access token without a supplying a valid token will
get you this (log back out first)::

    >>> self.logout()
    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     consumer=consumer1,
    ...     timestamp=timestamp,
    ... )
    >>> rt = token.GetAccessTokenPage(self.portal, request)
    >>> result = rt()
    Traceback (most recent call last):
    ...
    BadRequest...

Now for the token, but let's try to request an access token without the
correct verifier assigned::

    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     consumer=consumer1, 
    ...     token=atoken,
    ...     timestamp=timestamp,
    ... )
    >>> rt = token.GetAccessTokenPage(self.portal, request)
    >>> print rt()
    Traceback (most recent call last):
    ...
    BadRequest...

Okay, now do this properly with the verifier provided, as the consumer
just accessed the callback URL of the consumer to supply it with the
correct verifier::

    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     consumer=consumer1, 
    ...     token=atoken,
    ...     verifier=atoken_verifier,
    ...     timestamp=timestamp,
    ... )
    >>> rt = token.GetAccessTokenPage(self.portal, request)
    >>> accesstokenstr = rt()
    >>> print accesstokenstr
    oauth_token_secret=...&oauth_token=...
    >>> access_token = makeToken(accesstokenstr)

After verification, the old token should have been discarded and cannot
be used again to request a new token::

    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(
    ...     consumer=consumer1, 
    ...     token=atoken,
    ...     verifier=atoken_verifier,
    ...     timestamp=timestamp,
    ... )
    >>> rt = token.GetAccessTokenPage(self.portal, request)
    >>> rt()
    Traceback (most recent call last):
    ...
    Forbidden...

Now try again using the browser::

    >>> url = baseurl + '/OAuthGetAccessToken'
    >>> request = SignedTestRequest(
    ...     url=url,
    ...     consumer=consumer1,
    ...     token=btoken,
    ...     verifier=btoken_verifier,
    ...     timestamp=timestamp,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> baccesstokenstr = browser.contents
    >>> print baccesstokenstr
    oauth_token_secret=...&oauth_token=...
    >>> bacctoken = makeToken(baccesstokenstr)


------------------
Using OAuth Tokens
------------------

This is basic auth, which we want to avoid since consumers would have to
retain (thus know) the user/password combination::

    >>> baseurl = self.portal.absolute_url()
    >>> browser = Browser()
    >>> auth = '%s:%s' % (default_user, default_password)
    >>> browser.addHeader('Authorization', 'Basic %s' % auth.encode('base64'))
    >>> browser.open(baseurl + '/test_current_user')
    >>> print browser.contents
    test_user_1_

For the OAuth testing request, we need to generate the authorization
header proper, so we instantiate a signed request object and use it to
build this string::

    >>> url = baseurl + '/test_current_user'
    >>> request = SignedTestRequest(
    ...     consumer=consumer1, 
    ...     token=access_token, 
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 403: Forbidden

There is one more security consideration that needs to be satisified
still - the scope.

For now we omit its restrictions by overriding some of the fields
through unconventional injection of values::

    >>> scopeManager._mappings[scopeManager.default_mapping_id] = {
    ...     'Plone Site': ['test_current_user', 'test_current_roles'],
    ... }
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> print browser.contents
    test_user_1_

Try the roles view also, since it is also permitted::

    >>> url = baseurl + '/test_current_roles'
    >>> request = SignedTestRequest(
    ...     consumer=consumer1, 
    ...     token=access_token, 
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> print browser.contents
    Member
    Authenticated

If a client were to access a content type object without specifying a
view, typically the default view will be resolved.  If this is included
in the list of allowed names for the content type, the scope manager
will permit access.  Again a brute forced approach is taken to work
around scope manager restrictions::

    >>> scopeManager._mappings[scopeManager.default_mapping_id] = {
    ...     'Plone Site': ['test_current_user', 'test_current_roles'],
    ...     'Folder': ['folder_listing',],
    ... }
    >>> url = self.folder.absolute_url()
    >>> request = SignedTestRequest(
    ...     consumer=consumer1, 
    ...     token=access_token, 
    ...     url=url,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> 'There are currently no items in this folder.' in browser.contents
    True


---------------------------
Token Management Interfaces
---------------------------

The user (and site managers) would need to know what tokens are stored 
for who and also the ability to revoke tokens when they no longer wish 
to retain access for the consumer.  This is where the management form 
comes in.

Do note that as of this release, the URIs to the following management
interfaces are not made visible such as from the dashboard or the Site
Setup interfaces.  Site administrators may wish to add those links 
manually if they wish to make these functions more visible.

As our test user have granted access to two tokens already, they both
should show up if the listing page is viewed::

    >>> from pmr2.oauth.browser import user
    >>> self.login(default_user)
    >>> request = TestRequest()
    >>> view = user.UserTokenForm(self.portal, request)
    >>> result = view()
    >>> access_token.key in result
    True
    >>> 'consumer1.example.com' in result
    True

All the required data are present in the form.  Let's try to remove one
of the tokens using the test browser::

    >>> u_browser.open(baseurl + '/issued_oauth_tokens')
    >>> u_browser.getControl(name="form.widgets.key").controls[0].click()
    >>> u_browser.getControl(name='form.buttons.revoke').click()
    >>> len(tokenManager.getTokensForUser(default_user))
    1
    >>> result = u_browser.contents
    >>> 'Access successfully removed' in result
    True

Same deal for consumers, we can open the consumer management form and
we should see the single consumer that had been added earlier.  This
page can be accessed at `${portal_url}/manage-oauth-consumers`::

    >>> from pmr2.oauth.browser import consumer
    >>> request = TestRequest()
    >>> view = consumer.ConsumerManageForm(self.portal, request)
    >>> result = view()
    >>> 'consumer1.example.com' in result
    True

We can try to add a few consumers using the form also.  Since the client
in this case should be a browser, we will use the authenticated test
request class::

    >>> added_consumer_keys = []
    >>> from pmr2.testing.base import TestRequest as TestRequestAuthed
    >>> request = TestRequestAuthed(form={
    ...     'form.widgets.title': 'consumer2.example.com',
    ...     'form.buttons.add': 1,
    ... })
    >>> view = consumer.ConsumerAddForm(self.portal, request)
    >>> view.update()
    >>> added_consumer_keys.append(view._data['key'])

    >>> request = TestRequestAuthed(form={
    ...     'form.widgets.title': 'consumer3.example.com',
    ...     'form.buttons.add': 1,
    ... })
    >>> view = consumer.ConsumerAddForm(self.portal, request)
    >>> view.update()
    >>> added_consumer_keys.append(view._data['key'])

Now the management form should show these couple new consumers::

    >>> request = TestRequestAuthed()
    >>> view = consumer.ConsumerManageForm(self.portal, request)
    >>> result = view()
    >>> 'consumer2.example.com' in result
    True
    >>> 'consumer3.example.com' in result
    True

Should have no problems removing them either::

    >>> request = TestRequestAuthed(form={
    ...     'form.widgets.key': added_consumer_keys,
    ...     'form.buttons.remove': 1,
    ... })
    >>> view = consumer.ConsumerManageForm(self.portal, request)
    >>> result = view()
    >>> 'consumer2.example.com' in result
    False
    >>> 'consumer3.example.com' in result
    False


----------------------------
Scope Profile and Management
----------------------------

To properly restrict what resources can be accessed by consumers, access
granted by an access token is limited by scope managers, which was
demostrated earlier.  However, the adminstrators must have a way to
customize them.  To do that views and forms are provided::

    >>> from pmr2.oauth.browser import scope
    >>> from pmr2.testing.base import TestRequest as PMR2TestRequest
    >>> context = self.portal
    >>> request = PMR2TestRequest()
    >>> view = scope.ContentTypeScopeManagerView(context, request)
    >>> print view()
    <BLANKLINE>
    ...
    <h2>
      List of Scope Profiles.
    </h2>
    <ul>
    </ul>
    <p>
      <a href=".../add" id="ctsm_add_scope_profile">Add Scope Profile</a>
    </p>
    ...

Selecting that link will bring up the Add Scope Profile form::

    >>> request = PMR2TestRequest(form={
    ...     'form.widgets.name': 'test_profile',
    ...     'form.buttons.add': 1,
    ... })
    >>> view = scope.ContentTypeScopeProfileAddForm(context, request)
    >>> view.update()

Once that profile is added it will be first added as an edit profile, 
which are work in progress profiles to separate them from active ones.
This ensures that any existing access keys using the original scopes 
will not get retroactively updated by new scopes.

As stated, this can be retrieved and listed using the method provided by
the scope manager::

    >>> scopeManager.getEditProfile('test_profile')
    <pmr2.oauth.scope.ContentTypeScopeProfile object at ...>
    >>> scopeManager.getEditProfileNames()[0]
    'test_profile'

The manager view will list this also::

    >>> request = PMR2TestRequest()
    >>> view = scope.ContentTypeScopeManagerView(context, request)
    >>> print view()
    <BLANKLINE>
    ...
    <h2>
      List of Scope Profiles.
    </h2>
    <ul>
      <li>
        <a href=".../test_profile">test_profile</a>
      </li>
    </ul>
    <p>
      <a href=".../add" id="ctsm_add_scope_profile">Add Scope Profile</a>
    </p>
    ...

The link leads to the view form.  There should be some actions with
corresponding buttons::

    >>> request = PMR2TestRequest()
    >>> view = scope.ContentTypeScopeProfileDisplayForm(context, request)
    >>> view = view.publishTraverse(request, 'test_profile')
    >>> view.update()
    >>> result = view.render()
    >>> 'Commit Update' in result
    True
    >>> 'Edit' in result
    True
    >>> 'Revert' in result
    True

Now instantiate the edit view for that profile::

    >>> request = PMR2TestRequest()
    >>> view = scope.ContentTypeScopeProfileEditForm(context, request)
    >>> view = view.publishTraverse(request, 'test_profile')
    >>> view.update()
    >>> result = view.render()
    >>> 'Document' in result
    True
    >>> 'Folder' in result
    True

Apply the value and see that the profile is updated::

    >>> request = PMR2TestRequest(form={
    ...     'form.widgets.title': u'Test current user',
    ...     'form.widgets.description': u'See current user information.',
    ...     'form.widgets.mapping.widgets.Plone Site': u'test_current_user',
    ...     'form.widgets.mapping.widgets.Document': u'document_view',
    ...     'form.widgets.mapping-empty-marker': 1,
    ...     'form.buttons.apply': 1,
    ... })
    >>> view = scope.ContentTypeScopeProfileEditForm(context, request)
    >>> view = view.publishTraverse(request, 'test_profile')
    >>> view.update()
    >>> result = view.render()
    >>> profile = scopeManager.getEditProfile('test_profile')
    >>> profile.mapping['Document']
    ['document_view']

However, as currently implemented, views that were permitted for another
type that may have been installed previously will not be saved if the
profile is updated with the form.  Here we add a dummy mapping and then
update the form again and see that the views enabled for the Dummy type
is not preserved::

    >>> request.environ['pmr2.traverse_subpath'] = []
    >>> new_mapping = {}
    >>> new_mapping.update(profile.mapping)
    >>> new_mapping['Dummy'] = ['dummy_view']
    >>> profile.mapping = new_mapping
    >>> profile.mapping.get('Dummy', False)
    ['dummy_view']
    >>> view = scope.ContentTypeScopeProfileEditForm(context, request)
    >>> view = view.publishTraverse(request, 'test_profile')
    >>> view.update()
    >>> profile = scopeManager.getEditProfile('test_profile')
    >>> profile.mapping.get('Dummy', False)
    False

Back onto the edit form.  See that the profile can be committed for
use::

    >>> request = PMR2TestRequest(form={
    ...     'form.buttons.setdefault': 1,
    ... })
    >>> view = scope.ContentTypeScopeProfileDisplayForm(context, request)
    >>> view = view.publishTraverse(request, 'test_profile')
    >>> view.update()

Wait, the profile has not been committed.  There will be an error 
rendered, along with the notification that it has been modified.::

    >>> status = IStatusMessage(request)
    >>> messages = status.show()
    >>> messages[0].message
    u'This profile has not been committed yet.'
    >>> messages[1].message
    u'This profile has been modified. ...

Try this again after committing it::

    >>> request = PMR2TestRequest(form={
    ...     'form.buttons.commit': 1,
    ... })
    >>> view = scope.ContentTypeScopeProfileDisplayForm(context, request)
    >>> view = view.publishTraverse(request, 'test_profile')
    >>> view.update()

Use the newly created mapping as the default mapping::

    >>> request = PMR2TestRequest(form={
    ...     'form.buttons.setdefault': 1,
    ... })
    >>> view = scope.ContentTypeScopeProfileDisplayForm(context, request)
    >>> view = view.publishTraverse(request, 'test_profile')
    >>> view.update()
    >>> mapping_id = scopeManager.default_mapping_id
    >>> mapping_id
    1

Verify that the mapping and associated metadata is saved::

    >>> mapping = scopeManager.getMapping(mapping_id)
    >>> mapping['Document']
    ['document_view']
    >>> mapping['Folder']
    >>> scopeManager.getMappingMetadata(mapping_id) == {
    ...     'title': u'Test current user',
    ...     'description': u'See current user information.',
    ... }
    True


~~~~~~~~~~~~~~
Error Handling
~~~~~~~~~~~~~~

Traversing to profiles using edit form will get NotFound::

    >>> request = PMR2TestRequest()
    >>> view = scope.ContentTypeScopeProfileEditForm(context, request)
    >>> view.update()
    Traceback (most recent call last):
    ...
    NotFound...

    >>> request = PMR2TestRequest()
    >>> view = scope.ContentTypeScopeProfileEditForm(context, request)
    >>> view = view.publishTraverse(request, 'no_profile')
    >>> view.update()
    Traceback (most recent call last):
    ...
    NotFound...

    >>> request = PMR2TestRequest()
    >>> view = scope.ContentTypeScopeProfileDisplayForm(context, request)
    >>> view = view.publishTraverse(request, 'no_profile')
    >>> view.update()
    Traceback (most recent call last):
    ...
    NotFound...


~~~~~~~~~~~~~~~~~~~~~~
Through a web browser.
~~~~~~~~~~~~~~~~~~~~~~

To set up the scope management interface in a more natural manner, the
views use the base scope management view as the context.  This can
result in some unintended consequences and here these will be tested.

First log in as portal owner::

    >>> o_browser = Browser()
    >>> o_browser.open(baseurl + '/login')
    >>> o_browser.getControl(name='__ac_name').value = portal_owner
    >>> o_browser.getControl(name='__ac_password').value = default_password
    >>> o_browser.getControl(name='submit').click()

Now traverse to the content type scope profile management page.  The
created profile will be available for selection::

    >>> o_browser.open(baseurl + '/manage-ctsp')
    >>> contents = o_browser.contents
    >>> o_browser.getLink('test_profile').click()

A brief summary of the permitted views will be shown::

    >>> contents = o_browser.contents
    >>> 'document_view' in contents
    True

The edit button should be available.  Select that to open the edit form,
and see that the fields are populated with previously assigned values::

    >>> o_browser.getControl(name='form.buttons.edit').click()
    >>> ct = o_browser.getControl(name="form.widgets.mapping.widgets.Document")
    >>> ct.value
    'document_view'

Permit the viewing of folder contents and the two test views definied
for this test that are for the site root::

    >>> o_browser.getControl(name="form.widgets.mapping.widgets.Folder"
    ...      ).value = 'folder_listing'
    >>> o_browser.getControl(name="form.widgets.mapping.widgets.Plone Site"
    ...      ).value = 'test_current_roles'
    >>> o_browser.getControl(name='form.buttons.apply').click()
    >>> profile = scopeManager.getEditProfile('test_profile')
    >>> profile.mapping.get('Plone Site', False)
    ['test_current_roles']

Return to the main view and see that the profile is applied::

    >>> o_browser.getControl(name='form.buttons.cancel').click()
    >>> contents = o_browser.contents
    >>> 'test_current_roles' in contents
    True
    >>> 'This profile has been modified.' in contents
    True

Now commit the changes, and see if this profile is activated.  Note the
status message about the modified state is now visible again::

    >>> o_browser.getControl(name='form.buttons.commit').click()
    >>> contents = o_browser.contents
    >>> mapping = scopeManager.getMappingByName('test_profile')
    >>> mapping.get('Plone Site', False)
    ['test_current_roles']
    >>> mapping.get('Document', False)
    ['document_view']
    >>> 'This profile has been modified.' in contents
    False

Test for the functionality of the revert button also::

    >>> o_browser.getControl(name='form.buttons.edit').click()
    >>> o_browser.getControl(name="form.widgets.mapping.widgets.Plone Site"
    ...      ).value = 'test_current_user\r\ntest_current_roles'
    >>> o_browser.getControl(name='form.buttons.apply').click()
    >>> profile = scopeManager.getEditProfile('test_profile')
    >>> profile.mapping.get('Plone Site', False)
    ['test_current_user', 'test_current_roles']

    >>> o_browser.getControl(name='form.buttons.cancel').click()
    >>> 'This profile has been modified.' in o_browser.contents
    True
    >>> o_browser.getControl(name='form.buttons.revert').click()
    >>> 'This profile has been modified.' in o_browser.contents
    False
    >>> profile = scopeManager.getEditProfile('test_profile')
    >>> profile.mapping.get('Plone Site', False)
    ['test_current_roles']

Back to the main page, and try to add a new profile::

    >>> o_browser.open(baseurl + '/manage-ctsp')
    >>> contents = o_browser.contents
    >>> o_browser.getLink(id='ctsm_add_scope_profile').click()

    >>> o_browser.getControl(name="form.widgets.name").value = 'another'
    >>> o_browser.getControl(name="form.buttons.add").click()

    >>> o_browser.getControl(name="form.buttons.edit").click()

    >>> o_browser.getControl(name="form.widgets.title"
    ...     ).value = 'Access document contents'
    >>> o_browser.getControl(name="form.widgets.description"
    ...     ).value = 'Allow clients to view documents.'
    >>> o_browser.getControl(name="form.widgets.mapping.widgets.Document"
    ...      ).value = 'document_view'
    >>> o_browser.getControl(name="form.widgets.mapping.widgets.Plone Site"
    ...      ).value = 'test_current_user'
    >>> o_browser.getControl(name="form.buttons.apply").click()

    >>> o_browser.getControl(name="form.buttons.cancel").click()

    >>> o_browser.getControl(name="form.buttons.commit").click()

    >>> another_id = scopeManager.getMappingId('another')
    >>> another_mapping = scopeManager.getMapping(another_id)
    >>> another_mapping.get('Document')
    ['document_view']
    >>> scopeManager.getMappingMetadata(another_id) == {
    ...     'title': u'Access document contents',
    ...     'description': u'Allow clients to view documents.',
    ... }
    True


----------------------
Using OAuth with scope
----------------------

To properly take advantage of OAuth, scope must be managed and used
effectively to safeguard content owner's data.  Here we set up a new
tokens using the default profile.::

    >>> url = baseurl + '/OAuthRequestToken'
    >>> request = SignedTestRequest(consumer=consumer1, url=url, 
    ...     callback='oob',
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> toks1 = browser.contents
    >>> tok1 = makeToken(toks1)
    >>> tok1 = tokenManager.get(tok1.key)
    >>> tokenManager.claimRequestToken(tok1, default_user)

    >>> url = baseurl + '/OAuthGetAccessToken'
    >>> request = SignedTestRequest(url=url, consumer=consumer1, token=tok1,
    ...     verifier=tok1.verifier,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> tok1 = browser.contents
    >>> tok1 = makeToken(tok1)

Test out some of the views::

    >>> url = self.folder.absolute_url()
    >>> request = SignedTestRequest(consumer=consumer1, token=tok1, url=url)
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 403: Forbidden

    >>> url = self.portal.absolute_url() + '/test_current_user'
    >>> request = SignedTestRequest(consumer=consumer1, token=tok1, url=url)
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> browser.contents
    'test_user_1_'

The second token, however, will make use of the scope parameter to make
use of the scope profile we have defined earlier::

    >>> url = (baseurl +
    ...     '/OAuthRequestToken?scope=http://nohost/Plone/test_profile')
    >>> request = SignedTestRequest(consumer=consumer1, url=url, 
    ...     callback='oob',
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> toks2 = browser.contents
    >>> tok2 = makeToken(toks2)
    >>> tok2 = tokenManager.get(tok2.key)
    >>> tokenManager.claimRequestToken(tok2, default_user)

    >>> url = baseurl + '/OAuthGetAccessToken'
    >>> request = SignedTestRequest(url=url, consumer=consumer1, token=tok2,
    ...     verifier=tok2.verifier,
    ... )
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> tok2 = browser.contents
    >>> tok2 = makeToken(tok2)

Test out some of the views with the second token.  There will be a 
different set of views available::

    >>> url = self.folder.absolute_url()
    >>> request = SignedTestRequest(consumer=consumer1, token=tok2, url=url)
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)

    >>> url = self.portal.absolute_url() + '/test_current_user'
    >>> request = SignedTestRequest(consumer=consumer1, token=tok2, url=url)
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 403: Forbidden

    >>> url = self.portal.absolute_url() + '/test_current_roles'
    >>> request = SignedTestRequest(consumer=consumer1, token=tok2, url=url)
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    >>> print browser.contents
    Member
    Authenticated

As mentioned before, even with an updated profile, the previously used
scope for a given token is retained.  The first token issued in this
subsection had the outdated default scope which forbid access to folder
contents, so test that this is the case by using the owner's browser to
set the current test_profile as the default profile, then demonstrate
that the original permissions are still intact::

    >>> scopeManager.default_mapping_id
    1
    >>> o_browser.getControl(name='form.buttons.setdefault').click()
    >>> scopeManager.default_mapping_id
    3

    >>> url = self.folder.absolute_url()
    >>> request = SignedTestRequest(consumer=consumer1, token=tok1, url=url)
    >>> auth = request._auth
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', auth)
    >>> browser.open(url)
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 403: Forbidden


~~~~~~~~~~~~~~~~~~~~~~
Client specified scope
~~~~~~~~~~~~~~~~~~~~~~

Clients can specify the scope profiles that will be checked against when
accessing the contents of the resource owner.  These scope profiles will
be used instead of the default one.

If a specific scope was requested, the title, description and list of
subpaths permitted per each view will be made visible to the resource
owner::

    >>> scopetok1 = tokenManager.generateRequestToken(consumer1.key, 'oob')
    >>> scopeManager.requestScope(scopetok1.key,
    ...     'http://nohost/Plone/scope/another')
    True
    >>> u_browser.open(auth_baseurl + '?oauth_token=' + scopetok1.key)
    >>> print u_browser.contents
    <...
    <dl>
      <dt>Access document contents</dt>
      <dd>
        <p>Allow clients to view documents.</p>
      </dd>
    </dl>
    ...
      <dd...
    ...
        <p>
          The following is a detailed listing of all subpaths available
          per content type for tokens using this set of scope profiles.
        </p>
        <dl>
          <dt>Document</dt>
          <dd>
            <ul>
              <li>document_view</li>
            </ul>
          </dd>
        </dl>
        <dl>
          <dt>Plone Site</dt>
          <dd>
            <ul>
              <li>test_current_user</li>
            </ul>
          </dd>
        </dl>
      </dd>
    ...

Multiple scopes can be specified.  For the content type scope manager,
the scope argument is a list of comma-separated urls with paths ending
with a valid profile identifier.  If multiple profiles are specified,
the mappings will be merged together with the descriptions appropriately
updated::

    >>> scopetok2 = tokenManager.generateRequestToken(consumer1.key, 'oob')
    >>> scopeManager.requestScope(scopetok2.key,
    ...     'http://nohost/Plone/scope/another,'
    ...     'http://nohost/Plone/scope/test_profile')
    True
    >>> u_browser.open(auth_baseurl + '?oauth_token=' + scopetok2.key)
    >>> print u_browser.contents
    <...
    <dl>
      <dt>Access document contents</dt>
      <dd>
        <p>Allow clients to view documents.</p>
      </dd>
      <dt>Test current user</dt>
      <dd>
        <p>See current user information.</p>
      </dd>
    </dl>
    ...
      <dd...
    ...
        <p>
          The following is a detailed listing of all subpaths available
          per content type for tokens using this set of scope profiles.
        </p>
        <dl>
          <dt>Document</dt>
          <dd>
            <ul>
              <li>document_view</li>
            </ul>
          </dd>
        </dl>
        <dl>
          <dt>Folder</dt>
          <dd>
            <ul>
              <li>folder_listing</li>
            </ul>
          </dd>
        </dl>
        <dl>
          <dt>Plone Site</dt>
          <dd>
            <ul>
              <li>test_current_roles</li>
              <li>test_current_user</li>
            </ul>
          </dd>
        </dl>
      </dd>
    ...
