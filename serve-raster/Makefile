run:
	poetry run uvicorn serve_raster.main:app --reload

build:
	docker build --tag=wps-server-raster:latest .

run-docker:
	docker run -t --env-file=".env" -p 8000:8000 wps-server-raster:latest