from setuptools import setup, find_packages
import os

version = '0.5.1'

setup(name='pmr2.oauth',
      version=version,
      description="OAuth PAS Plugin, OAuth 1.0 provider for Plone.",
      long_description=open("README.rst").read() + "\n" +
           open(os.path.join("docs", "HISTORY.rst")).read(), 
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Framework :: Plone :: 4.0",
        "Framework :: Plone :: 4.1",
        "Framework :: Plone :: 4.2",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Tommy Yu',
      author_email='tommy.yu@auckland.ac.nz',
      url='https://github.com/PMR2/pmr2.oauth',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['pmr2'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'oauthlib==0.6.0',
          'zope.testing',
          'zope.component',
          'zope.interface',
          'zope.schema',
          'zope.annotation',
          'pmr2.z3cform',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
