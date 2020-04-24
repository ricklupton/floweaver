# Developer docs for floWeaver

This document describes how to work on the floWeaver code itself: setting up the
environment, running tests, building the docs, and releasing a new version.

## Setting up a development venv

You don't have to do this -- you can work on floWeaver using any Python
installation you like. But it's often useful to have a separate environment for
each project.

```shell
# Create an environment (change path to whatever you like)
$ python -m venv ~/path/to/env

# Activate the environment
$ source ~/path/to/env/bin/activate

# In the floWeaver directory: install editable with test deps
$ pip install -e '.[test,docs]'
```

Now you can activate this environment whenever you want to work on floweaver (to
deactivate run `deactivate`).

## Running tests

We use [pytest](https://pytest.org) to run tests.

With the floWeaver environment activated as above (if using):
```shell
$ python -m pytest
```

(just `pytest` should work, but I find sometimes it uses the wrong Python
version when working in venvs)

## Building the docs

The docs are built with [Sphinx](http://sphinx-doc.org). When making changes to
the docs you can rebuild them locally to see the results. The online version is
rebuilt automatically by ReadTheDocs.

```shell
$ cd docs
$ make html
```

This can take a few minutes the first time because the example Jupyter notebooks
are run automatically. Subsequent runs after updates should be quicker.

Open `docs/_build/html/index.html` in your browser to see the results.

Cookbook/tutorial notebooks should be saved without outputs and with widget data
cleared, as they are run during the process of building the notebooks. New
examples should be added to the index.rst file.

## Releasing a new version

1. Remove -dev from the version
2. Commit "Releasing version"
3. Add tag with version number
4. `python setup.py sdist`
5. `python setup.py bdist_wheel`
6. `twine upload dist/*`
7. Increase version number and add -dev
8. Commit "Bump version"
