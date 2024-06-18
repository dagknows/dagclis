

all: cleanall build 

cleanall:
	rm -Rf dist ; rm -Rf build ; rm -Rf *.egg-info

build:
	python -m build . --wheel
	twine check dist/*

	# pip-compile pyproject.toml

test:
	coverage run --omit './env/*' --omit '/usr/*' -m unittest tests/*.py
	coverage report

