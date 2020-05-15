#!/usr/bin/env python
# Always prefer setuptools over distutils
from setuptools import setup, find_packages

__doc__ = """
To install as system package:

  python setup.py install
  
To install as local package:

  RU=/opt/control
  python setup.py egg_info --egg-base=tmp install --root=$RU/files --no-compile \
    --install-lib=lib/python/site-packages --install-scripts=ds

-------------------------------------------------------------------------------
"""

version = open('VERSION').read().strip()
scripts = ['ProcessProfiler']
license = 'GPL-3.0'

package_dir = {
    'ProcessProfiler': '.',
}
packages = package_dir.keys()

package_data = {
    '': [version],
}

packages = package_dir.keys()


setup(name = 'processprofiler',
      version = version,
      license = license,
      description = 'Tango device for collecting cpu and process stats',
      packages = packages,
      package_dir= package_dir,
      scripts = scripts,
      include_package_data = True,
      package_data = package_data
     )
