# Requires:
#  subversion 
#  virtualenv
#
APPNAME = bipostal
TOP = $(shell pwd)
VE = virtualenv
PY = $(TOP)/bin/python
EZ = $(TOP)/bin/easy_install
NO = $(TOP)/bin/nosetests -s --with-xunit

build: clean init

clean:
	rm -rf build
	rm -rf dist
	rm -rf man

init:
	$(VE) --no-site-packages --distribute .
	bin/pip install -r dev-reqs.txt
	svn checkout http://ppymilter.googlecode.com/svn/trunk ppymilter
	cd ppymilter; $(PY) ./setup.py install

test:
	$(NO) src


