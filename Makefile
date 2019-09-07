ifndef PYTHON
PYTHON=python
endif

all-local:
	$(PYTHON) setup.py build

clean:	setup.py
	$(PYTHON) setup.py clean
	-rm -rf build
	-rm -rf dist
	-rm -f MANIFEST
	-find . -name "*.pyc" -delete
