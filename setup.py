from setuptools import setup, find_packages
import os

version = '0.4'

setup(name='pmr2.oauth',
      version=version,
      description="OAuth PAS Plugin",
      long_description=open("README.rst").read() + "\n" +
           open(os.path.join("pmr2", "oauth", "README.rst")).read() + '\n' +
           open(os.path.join("docs", "UPGRADE.rst")).read() + '\n' +
           open(os.path.join("docs", "HISTORY.rst")).read(), 
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
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
          'oauthlib<0.4',
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
