from setuptools import setup, find_packages
import sys, os

version = '0.9'
shortdesc = 'node.ext.mdb'
longdesc = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

setup(name='node.ext.mdb',
      version=version,
      description=shortdesc,
      long_description=longdesc,
      classifiers=[
            'Development Status :: 4 - Beta',
            'Operating System :: OS Independent',
            'Programming Language :: Python', 
            'Topic :: Utilities',
      ],
      keywords='',
      author='BlueDynamics Alliance',
      author_email='dev@bluedynamics.com',
      url=u'',
      license='GNU General Public Licence',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['node', 'node.ext'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'node',
          'lxml',
          # -*- Extra requirements: -*
      ],
      extras_require = dict(
          test=[
                'interlude',
          ]
      ),
      tests_require=['interlude'],
      test_suite="node.ext.mdb.tests.test_suite"
      )