

all: cleanall test build 

cleanall:
	rm -Rf dist ; rm -Rf build ; rm -Rf *.egg-info

build:
	python -m build . --wheel
	twine check dist/*

test:
	coverage run --omit './env/*' --omit '/usr/*' -m unittest tests/*.py
	coverage report

prepublish:
	pip-compile pyproject.toml

