============
Introduction
============

This module provides basic OAuth support for Zope/Plone while aiming to
be extensible through the Zope Component Architecture such that more
demanding features can be slotted in.  Basic features will be provided,
such as simple management of consumers and their keys, and local users
will be able to approve consumer requests and revoke the keys later.

Currently this package should be treated as a proof of concept, thus
completely unsuitable for production use.


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


-----
Usage
-----

For further usage information, please refer to the tests and the 
associated README files (i.e. pmr2/oauth/README.rst)
