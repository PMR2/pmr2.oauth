from logging import getLogger
from zope.component.hooks import getSite

from Products.CMFCore.utils import getToolByName


def createPlugin(site, id_):
    logger = getLogger('pmr2.oauth')
    acl = getToolByName(site, "acl_users")
    acl.manage_addProduct["pmr2.oauth"].addOAuthPlugin(
            id=id_, title='OAuth authentication plugin')


def activatePlugin(site, id_):
    logger = getLogger('pmr2.oauth')
    acl = getToolByName(site, "acl_users")
    plugin = getattr(acl, id_)
    interfaces = plugin.listInterfaces()

    activate = []

    for info in acl.plugins.listPluginTypeInfo():
        interface = info["interface"]
        interface_name = info["id"]
        if plugin.testImplements(interface):
            activate.append(interface_name)
            logger.info("Activating interface %s for plugin %s" % 
                    (interface_name, info["title"]))

    plugin.manage_activateInterfaces(activate)


def importVarious(context):
    # Only run step if a flag file is present (e.g. not an extension profile)
    if context.readDataFile('oauth-pas.txt') is None:
        return

    id_ = 'oauth'
    site = context.getSite()

    acl = getToolByName(site, "acl_users")
    installed = acl.objectIds()
    if id_ not in installed:
        createPlugin(site, id_)
        activatePlugin(site, id_)


def migrate_v0_2_to_v_0_4(context):
    logger = getLogger('pmr2.oauth')
    logger.info('Migrating pmr2.oauth to v0.4.')
    site = getSite()
    scope_upgrade_v0_4(site)
    context.runAllImportStepsFromProfile('profile-pmr2.oauth:default')

def scope_upgrade_v0_4(site):
    import zope.component
    from zope.annotation import IAnnotations
    from pmr2.oauth.interfaces import ITokenManager, IConsumerManager

    logger = getLogger('pmr2.oauth')
    ants = IAnnotations(site)
    if 'pmr2.oauth.scope.DefaultScopeManager' in ants:
        logger.info('Purging the removed DefaultScopeManager.')
        del ants['pmr2.oauth.scope.DefaultScopeManager']

    # The following needs to be done because of the uselessness of a
    # token without a scope, not to mention the impossibility of
    # migrating the scope definitions from previous scope manager.
    logger.info('Purging and reinitializing the built-in token manager.')
    tm = zope.component.getMultiAdapter((site, None), ITokenManager)
    tm.__init__()
