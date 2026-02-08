# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = Sankey-view
SOURCEDIR     = .
BUILDDIR      = _build
JSDIR         = ../js

# JS executor sources
JS_SOURCES    = $(wildcard $(JSDIR)/src/*.js) $(JSDIR)/rollup.config.js

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Build the JS executor bundle into the demo directory
_extra/execute-spec-demo/floweaver-executor.esm.js: $(JS_SOURCES)
	cd "$(JSDIR)" && npm run build
	cp "$(JSDIR)/dist/floweaver-executor.esm.js" _extra/execute-spec-demo/floweaver-executor.esm.js

# Common Sphinx targets with explicit JS bundle dependency
.PHONY: help html dirhtml singlehtml json latex latexpdf text man clean

html dirhtml singlehtml json latex latexpdf text man: _extra/execute-spec-demo/floweaver-executor.esm.js
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)