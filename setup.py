from setuptools import setup

from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='sankeyview',
    version='0.1.0',
    description='Sankey diagrams as views on datasets',
    long_description=long_description,

    author='Rick Lupton',
    author_email='rcl33@cam.ac.uk',

    license='MIT',

    packages=['sankeyview'],

    install_requires=[
        'numpy',
        'pandas',
        'numexpr',
        'xlrd',
        'networkx',
        'palettable',
    ],

    entry_points={
        'console_scripts': [
            # 'sankeysolver=sankeysolver.__main__:cli',
        ]
    }
)
