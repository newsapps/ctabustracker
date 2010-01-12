#!/bin/env python

from setuptools import setup, find_packages

setup(name='ctabustracker',
    version='0.1dev',
    description='A python wrapper for the Chicago Transit Authority\'s Bustracker API.',
    long_description='',
    author='Christopher Groskopf',
    author_email='cgroskopf@tribune.com',
    packages=find_packages(),
    install_requires=['BeautifulSoup'],
    )