PY ?= python

all: data run

data:
	$(PY) -m ops.generate_data

run:
	$(PY) -m ops.pipeline

test:
	$(PY) -m pytest -q

.PHONY: all data run test
