PACKAGE = vertigo

WITH_DOCTEST = --with-doctest --doctest-extension=rst
WITH_COVERAGE = --with-coverage --cover-branches --cover-inclusive --cover-erase --cover-package=${PACKAGE}
FILES = ${PACKAGE}/*.py tests/ README*.rst

smoke:
	nosetests -x ${WITH_DOCTEST} ${FILES}

test:
	nosetests ${WITH_DOCTEST} ${WITH_COVERAGE} ${FILES}

html: test
	coverage html --include='${PACKAGE}/*'

flakes:
	pyflakes .
