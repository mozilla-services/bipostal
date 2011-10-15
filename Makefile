# Requires:
#  subversion 
#  virtualenv
#
APPNAME = bipostal
TOP = $(shell pwd)
VE = virtualenv
PY = $(TOP)/bin/python
EZ = $(TOP)/bin/easy_install

build: 
		$(VE) --no-site-packages --distribute .
		svn checkout http://ppymilter.googlecode.com/svn/trunk ppymilter
		cd ppymilter; $(PY) ./setup.py install

