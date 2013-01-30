====================
Upgrading pmr2.oauth
====================

The following are required reading for users wishing to upgrade
pmr2.oauth, as this add-on is not yet matured so many items are still
rather unstable.

---------------
From 0.2 to 0.4
---------------

A word of caution before replacing 0.2 with 0.4: the changes made to the
default scope manager is a complete rewrite, as the security it offered
was merely a quick and dirty demonstration.  Due to this change, all
existing tokens and scopes will need to be purged, and clients
(consumers) will need to request new access tokens from the resource
owners.

If you wish to continue with this upgrade, please upgrade by going into
the Zope Management Interface, portal_setup, upgrades, and select the
``pmr2.oauth:default`` profile.  If no profiles appear, there should be
an option to show old upgrades.  Select that, select the `pmr2.oauth
upgrade to v0.4` step and upgrade.  Running this step will also
reinstall the product to ensure the activation of the accompanied
pmr2.z3cform helper library.

Another note: consumers now have their keys randomly generated, with the
human-friendly names moved to its own fields.  The recommendation is to
remove all previous keys and issue new ones, but this step is not done
automatically.  Old keys should still be usable, but they won't be as
friendly to the end users as they will lack the human-friendly
component.
