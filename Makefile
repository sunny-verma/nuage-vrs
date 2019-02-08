#!/usr/bin/make
PYTHON := /usr/bin/env python
NOSE := /usr/bin/env nosetests
lint:
	@flake8 --exclude hooks/charmhelpers hooks unit_tests
	@charm proof


test:
	@# Bundletester expects unit tests here.
	@echo Starting unit tests...
	@$(NOSE) -v --nologcapture --with-coverage unit_tests
	@#$(PYTHON) /usr/bin/nosetests -v --nologcapture --with-coverage unit_tests

