#!/bin/env python

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

setup(name='ctabustracker',
    version='0.1dev',
    description='A thin wrapper around the CTA Bus Tracker API.',
    long_description='',
    author='Christopher Groskopf',
    author_email='cgroskopf@tribune.com',
    url='???',
    packages=find_packages(),
    install_requires=['BeautifulSoup'],
    )