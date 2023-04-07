

all: cleanall test build 

cleanall:
	rm -Rf dist ; rm -Rf build ; rm -Rf *.egg-info

build:
	python -m build . --wheel

test:
	coverage run -m unittest tests/*.py
	coverage report
