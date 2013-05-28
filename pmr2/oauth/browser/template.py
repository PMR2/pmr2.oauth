from os.path import join
from os.path import dirname

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

root = dirname(__file__)
path = lambda x: join(root, 'template', x)
