notebook:
	PYTHONPATH=$(shell pwd) JUPYTER_PATH=$(shell pwd) poetry run jupyter notebook --ip 0.0.0.0

run:
	poetry run python fire_perimeter/client.py

build:
	docker build --tag=wps-fire-perimeter:latest .

run-docker:
	docker run --network="host" -t --env-file=".env" wps-fire-perimeter:latest