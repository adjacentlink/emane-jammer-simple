EXTRA_DIST= \
 README \
 README.md \
 setup.py.in \
 autogen.sh \
 emane_jammer_simple \
 scripts \
 m4 \
 debian \
 $(PACKAGE).spec.in

BUILT_SOURCES = \
 setup.py \
 $(PACKAGE).spec \
 emane_jammer_simple/service/emane_jammer_simple_pb2.py

all-local:
	$(PYTHON) setup.py build

dist-hook:
	find $(distdir) -name "*_pb2.py" -delete

clean-local: setup.py
	$(PYTHON) setup.py clean
	-rm -rf build
	-rm -rf dist
	-rm -f $(BUILT_SOURCES)
	-find . -name "*.pyc" -delete
	-find . -name "__pycache__" -delete
	-rm -rf waveform_resource.egg-info
	-rm -f $(PACKAGE)-*.tar.gz
	-rm -f $(PACKAGE).spec
	-rm -f .installedfiles
	-rm -rf .rpmbuild
	-rm -rf .debbuild

DISTCLEANFILES=setup.py

sdist:
	$(PYTHON) setup.py sdist

edit = sed                              \
        -e 's|@VERSION[@]|$(VERSION)|g' \
        -e 's|@PYTHON[@]|$(PYTHON)|g'   \
        -e 's|@DEBIAN_VERSION[@]|$(DEBIAN_VERSION)|g' \
        -e 's|@DATE_RFC2822[@]|$(DATE_RFC2822)|g'

setup.py:	setup.py.in
	if test -f $@; then chmod u+w $@; fi
	$(edit) $< > $@
	chmod g-w,u-w $@

install-exec-hook: $(BUILT_SOURCES)
	$(PYTHON) setup.py install \
        -O1 \
        --single-version-externally-managed \
        --record .installedfiles \
        --prefix=$(prefix) \
        --exec-prefix=$(exec_prefix) \
        $(if $(DESTDIR),--root=$(DESTDIR)) \
        $(if $(subst false,,$(HAVE_DEB)),--install-layout=deb)

uninstall-hook:
	if test -f .installedfiles; then xargs -a .installedfiles rm -f; fi

RPMARCH=`arch`

if HAVE_RPMBUILD

rpm: $(PACKAGE).spec dist-gzip
	mkdir -p .rpmbuild/BUILD \
	.rpmbuild/SPECS \
	.rpmbuild/SOURCES \
	.rpmbuild/SRPMS \
	.rpmbuild/RPMS/noarch \
	.rpmbuild/tmp
	cp -f $(PACKAGE)-$(VERSION).tar.gz .rpmbuild/SOURCES
	rpmbuild --clean -ba $(top_srcdir)/$(PACKAGE).spec --target $(RPMARCH) \
    --define "_topdir $$PWD/.rpmbuild" \
    --define "_tmppath $$PWD/.rpmbuild/tmp"
	@echo "============================================================"
	@echo "RPMs located in .rpmbuild/RPMS and .rpmbuild/SRPMS"

endif


if HAVE_DEB

deb: dist-gzip
	rm -rf .debbuild
	mkdir -p .debbuild
	cp -f $(PACKAGE)-$(VERSION).tar.gz .debbuild
	cd .debbuild && tar xzf $(PACKAGE)-$(VERSION).tar.gz
	$(edit) .debbuild/$(PACKAGE)-$(VERSION)/debian/changelog.in > \
          .debbuild/$(PACKAGE)-$(VERSION)/debian/changelog
	cd .debbuild/$(PACKAGE)-$(VERSION) && dpkg-buildpackage -F -us -uc
	@echo "============================================================"
	@echo "debs located in .debbuild"
cleandeb:
	dh_clean
else

cleandeb:

endif


$(PACKAGE).spec: $(PACKAGE).spec.in
	if test -f $@; then chmod u+w $@; fi
	$(edit) $< > $@
	chmod g-w,u-w $@

emane_jammer_simple/service/emane_jammer_simple_pb2.py: emane_jammer_simple/service/emane-jammer-simple.proto
	protoc -Iemane_jammer_simple/service --python_out=emane_jammer_simple/service  $<
