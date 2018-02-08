# To use a consistent encoding
import codecs
import re
from os import path

# Always prefer setuptools over distutils
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))


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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='Sankey diagram flow data visualisation',
    packages=find_packages(exclude=['docs', 'tests']),
    install_requires=[
        'numpy',
        'pandas',
        'networkx (>=1,<2)',
        'attrs',
        'palettable',
    ],
    extras_require={
        'dev': [],
        'test': [],
    },
)
