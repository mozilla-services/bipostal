# Requires:
#  subversion 
#  virtualenv
#
APPNAME = bipostal
TOP = $(shell pwd)
VE = virtualenv
PY = $(TOP)/bin/python
EZ = $(TOP)/bin/easy_install
NO = $(TOP)/bin/nosetests --with-xunit

clean:
		rm -rf build
		rm -rf dist
		rm -rf man

init:
	bin/pip install -r dev-reqs.txt

test:
	$(NO) $(APPNAME)

build: 
		$(VE) --no-site-packages --distribute .
		bin/pip install -r dev-reqs.txt
		svn checkout http://ppymilter.googlecode.com/svn/trunk ppymilter
		cd ppymilter; $(PY) ./setup.py install

