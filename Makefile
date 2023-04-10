

all: cleanall test build 

cleanall:
	rm -Rf dist ; rm -Rf build ; rm -Rf *.egg-info

build:
	python -m build . --wheel

test:
	coverage run --omit './env/*' --omit '/usr/*' -m unittest tests/*.py
	coverage report
