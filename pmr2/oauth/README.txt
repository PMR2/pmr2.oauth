==============
OAuth for PMR2
==============

This module provides OAuth authentication for PMR2.  Could probably be
used elsewhere in Plone.
::

    >>> import time
    >>> import oauth2 as oauth
    >>> import zope.component
    >>> from pmr2.oauth.interfaces import *
    >>> from pmr2.oauth.browser import *
    >>> from pmr2.oauth.consumer import *
    >>> from pmr2.oauth.tests.base import TestRequest
    >>> from pmr2.oauth.tests.base import SignedTestRequest

The default OAuth utility should be registered.
::

    >>> utility = zope.component.getUtility(IOAuthUtility)
    >>> utility
    <pmr2.oauth.utility.OAuthUtility object at ...>

The request adapter should have been registered:
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

    >>> consumer1 = Consumer('consumer1-key', 'consumer1-secret')
    >>> consumerManager.add(consumer1)
    >>> consumer1 == consumerManager.get('consumer1-key')
    True

It will be possible to use the browser form to add one also.


-----------------
Consumer Requests
-----------------

Once the consumer is registered onto the site, it is now possible to
use it to request token.  We can try a standard request without any
authorization.
::

    >>> request = TestRequest()
    >>> rt = RequestTokenPage(self.portal, request)
    >>> rt()
    Traceback (most recent call last):
    ...
    BadRequest

Now we construct a request signed with the key, using python-oauth2.
::

    >>> timestamp = str(int(time.time()))
    >>> request = SignedTestRequest(oauth_keys={
    ...     'oauth_version': "1.0",
    ...     'oauth_nonce': "4572616e48616d6d65724c61686176",
    ...     'oauth_timestamp': timestamp,
    ...     'oauth_callback': 'http://www.example.com/oauth/callback',
    ... }, consumer=consumer1)
    >>> rt = RequestTokenPage(self.portal, request)
    >>> result = rt()
    >>> print result
    oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true
