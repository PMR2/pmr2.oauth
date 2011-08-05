==============
OAuth for PMR2
==============

This module provides OAuth authentication for PMR2.  Could probably be
used elsewhere in Plone.
::

    >>> import zope.component
    >>> from pmr2.oauth.interfaces import *
    >>> from pmr2.oauth.browser import *
    >>> from pmr2.oauth.tests.base import TestRequest

The default OAuth utility should be registered.
::

    >>> utility = zope.component.getUtility(IOAuthUtility)
    >>> utility
    <pmr2.oauth.utility.OAuthUtility object at ...>


------------------------------
Client (Consumer) Registration
------------------------------

In order for a client to use the site contents, it needs to register
onto the site.


-----------------
Consumer Requests
-----------------

Once the consumer is registered onto the site, it can start redirecting
its user to resources here.


