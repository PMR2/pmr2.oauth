from os.path import join
import zope.i18nmessageid
from AccessControl.Permissions import manage_users as ManageUsers
from Products.PluggableAuthService.PluggableAuthService import \
    registerMultiPlugin

MessageFactory = zope.i18nmessageid.MessageFactory('pmr2.oauth')

from pmr2.oauth.plugins import oauth


registerMultiPlugin(oauth.OAuthPlugin.meta_type)

def initialize(context):
    # XXX should validate whether we have SSL installed.

    context.registerClass(oauth.OAuthPlugin,
        permission=ManageUsers,
        constructors=(
            oauth.manage_addOAuthPlugin,
            oauth.addOAuthPlugin,
        ),
        visibility=None,
        icon=join('browser', 'images', 'oauth.png'),
    )
