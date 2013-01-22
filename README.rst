============
Introduction
============

This module provides OAuth support for Zope/Plone, with the option to be
extensible through the Zope Component Architecture to allow the addition
of more feature-rich components.  Features core to OAuth are fully
supported, this includes the full OAuth authentication workflow, client
(consumer) management for site managers and access token management for
resource owners.  Scope restriction is also supported; site managers can
define content types and subpaths that are available for client usage
using scope profiles, and clients can specify a list of them to better
inform the resource owners of what will be accessed under their access
rights.

While the test coverage is fairly complete and demonstrates that access
permissions and scope restriction function as intended, the author does
not currently endorse the usage of this package in a mission critical
environment as there may be issues that can compromise the security of
such sites, as no audits have been done on this package by security
experts.  For providing third-party access to casually private data that
is not highly sensitive in nature, this package should be sufficiently
adequate in addressing that need.


------------
Installation
------------

This package may require Plone 4 or later.  Might work with Plone 3.3.x
but it has not been tested on that yet.


~~~~~~~~~~~~~~~~~~~~~~~~
Installing with buildout
~~~~~~~~~~~~~~~~~~~~~~~~

You can install pmr2.oauth using `buildout`_ by adding an entry for this
package in both eggs and zcml sections.

.. _buildout: http://pypi.python.org/pypi/zc.buildout

Example::

    [buildout]
    ...

    [instance]
    ...

    eggs =
        ...
        pmr2.oauth

    zcml =
        ...
        pmr2.oauth

Run buildout, then restart the Zope/Plone instance.  This package must
also be activated using the Add-ons panel under Site Setup within the
Plone instance where OAuth based authorization is to be used.


------------------------------------------
Further information and usage instructions
------------------------------------------

If the add-on is correctly installed and activated, an index of views
made available as part of this add-on can be found at
``${portal_url}/@@pmr2-oauth``.

If you are upgrading from a previously installed version of this add-on,
please refer to ``docs/UPGRADE.rst`` for some important information.

For more detailed information, please refer to the doctest file at
``pmr2/oauth/README.rst``.
