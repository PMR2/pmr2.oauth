=========
Changelog
=========

----------------
0.4 - 2013-01-22
----------------

~~~~~~~~~~~~~~~~~~~~~~~~~~~
Major architectural changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Removal of python-oauth2 and use oauthlib.  Significant changes to the
  PAS OAuthPlugin, including the removal of all private methods,
  replacement of the OAuthUtility with an adapter, with nearly all
  authentication and verification functions moved into this adapter,
  which extends the oauthlib server class.
* Scope manager completely redefined to accept any identifiers, which
  can be client (consumer), temporary or access keys.  Specific
  implementations can then make use of this change.
* Default scope manager no longer manages permitted URIs based directly
  on regex, but views and subpaths within specific content types.
* Consumer keys now randomly generated.  For identification purposes the
  title and domain fields are introduced.  Domain field serves an
  additional purpose for verification of callbacks by the default
  callback manager.

~~~~~~~~~~~~
New features
~~~~~~~~~~~~

* Introduction of callback manager.  This manages permitted targets for
  callbacks, so that resource owners will not be redirected to untrusted
  hosts especially for oob clients.
* Default scope manager provides the concept of scope profiles, which
  are concise representations of access that will be granted by the
  resource owner to clients.
* Base classes for extending/replacing provided functionalities.
* An index of all valid endpoints (views) made available by this add-on.

~~~~~~~~~~~~~~~~~~~~~~
Bugs (and maybe fixes)
~~~~~~~~~~~~~~~~~~~~~~

* The missing permissions.zcml is now included.  (noted by ngi644)
* Translations are not included with this release as there were too many
  new and modified text.

-----------------
0.3a - 2012-11-23
-----------------

* Scope manager now permit POST requests.
* Corrected the scope verification to be based on the resolved internal
  script URL.
* Corrected the signature verification method to use the actual URL, not
  the internal script URL.
* Workaround the adherence to legacy part of the spec in python-oauth2.

Note: This is a special release for development of PMR2-0.7 (or Release 
7), as this package now depends on some packages not yet released.  This
release is made regardless as it is needed for demonstration purposes.

----------------
0.2 - 2012-10-16
----------------

* Completing i18n coverage and added Italian support.  [giacomos]
* Added intermediate form class to eliminate the need to define wrapper
  classes for compatibility between Plone and z3c.form.

----------------
0.1 - 2011-10-20
----------------

* Provide the core functionality of OAuth into Zope/Plone, through the
  use of custom forms and the Pluggable Authentication System.
* Contain just the basic storage for all associated data types, but
  extensibility is allowed.
