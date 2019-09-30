#!/usr/bin/env python3

from distutils.core import setup

setup(name='MetaMaker',
      version='0.1',
      description='Utility to build MetaPackages',
      author='Raul Rodrigo Segura',
      author_email='raurodse@gmail.com',
      url='https://svn.lliurex.net/trusty/lliurex-meta-maker',
      packages=['metamaker'],
      package_dir={'':'src'},
      scripts=['bin/lliurex-meta-maker','bin/lliurex-meta-list-generator','bin/lliurex-meta-list-search']
     )
