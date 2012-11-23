=========
Changelog
=========

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
* Added intermediate form class to eliminate the neeed to define wrapper
  classes for compatibility between Plone and z3c.form.

----------------
0.1 - 2011-10-20
----------------

* Provide the core functionality of OAuth into Zope/Plone, through the
  use of custom forms and the Pluggable Authentication System.
* Contain just the basic storage for all associated data types, but
  extensibility is allowed.
