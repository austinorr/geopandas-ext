#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Usage: $pip install .

from setuptools import setup, find_packages

with open('geopandas_ext//__init__.py') as info_file:
    version = author = email = ""
    for line in info_file:
        if line.startswith('__version__'):
            version = line.split("=")[1].replace("'","").strip()
        elif line.startswith('__author__'):
            author = line.strip().split("=")[1].replace("'","").strip()
        elif line.startswith('__email__'):
            email = line.strip().split("=")[1].replace("'","").strip()

# with open('README.rst') as readme_file:
#     readme = readme_file.read()

requirements = ["numpy", "pandas", "fiona", 
                "shapely", "geopandas", "requests", "pyepsg",
                "rtree", "libspatialindex",
                ]

test_requirements = ['pytest>=3.1']

setup(
    name='geopandas_ext',
    version=version,
    description="Enhancements for `geopandas`",
    long_description="",# TODO: readme,
    author=author,
    author_email=email,
    url='https://github.com/austinorr/geopandas_ext',
    packages=find_packages(),
    package_data=PACKAGE_DATA,
    include_package_data=True,
    install_requires=requirements,
    extras_require={'testing': test_requirements},
    license="BSD license",
    zip_safe=False,
    keywords=['gis', 'spatial overlay', 'pandas', 'geopandas'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Geospatial Analysts, Scientists, Engineers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='geopandas_ext.tests',
    tests_require=test_requirements
)
