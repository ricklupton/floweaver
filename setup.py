# To use a consistent encoding
import codecs
import re
from os import path
import sys

# Always prefer setuptools over distutils
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

# This check is here if the user does not have a new enough pip to recognize
# the minimum Python requirement in the metadata.
if sys.version_info < (3, 4):
    error = """
floWeaver 2.0.0+ does not support Python 2.x, 3.0, 3.1, 3.2, or 3.3.
Python 3.4 and above is required. This may be due to an out of date pip.
Make sure you have pip >= 9.0.1.
"""
    sys.exit(error)


def read(*parts):
    with codecs.open(path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# Get the long description from the README file
with codecs.open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='floweaver',
    version=find_version('floweaver', '__init__.py'),
    description="View flow data as Sankey diagrams.",
    long_description=long_description,
    url='https://github.com/ricklupton/floweaver',
    author='Rick Lupton',
    author_email='mail@ricklupton.name',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='Sankey diagram flow data visualisation',
    packages=find_packages(exclude=['docs', 'tests']),
    python_requires='>=3.5',
    install_requires=[
        'numpy',
        'pandas',
        'networkx >=2.1',
        'attrs >=17.4',
        'palettable',
    ],
    extras_require={
        'dev': [],
        'test': ['pytest', 'matplotlib', 'codecov', 'pytest-cov'],
        'docs': ['sphinx', 'nbsphinx', 'jupyter_client', 'ipykernel', 'ipysankeywidget']
    },
)
