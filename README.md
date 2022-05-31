# Fire Boundaries using Google Earth Engine

[![Lifecycle:Experimental](https://img.shields.io/badge/Lifecycle-Experimental-339999)](https://github.com/bcgov/repomountie/blob/master/doc/lifecycle-badges.md)

Google Earth Engine does not work on versions newer than 3.8.*

## About

# Fire Boundaries

Goal: Generate fire perimeter from satellite imagery. Remove need for manual generation using helicopter.
Issues: Dependant on cloud cover!
Issues: Need a government google account to productionize this.

- [x] command line: Generate raster (burn area + rgb) given bounding area & date.
- [ ] command line: Output must contain metadata (we need to know the source).
- [x] command line: Generate polygon given bounding area.
- [ ] command line: Generate polygon + raster given minimum bounding area & date - bounding area increases automatically to match fire area.
- [x] command line: Generate N polygon + raster pairs based on public currently active fires greater than Y hectares.
- [ ] command line: polygon + raster generated are uploaded to object store.
- [x] openshift cronjob: job runs automatically on a daily basis.
- [ ] spin up an instance of geoserver.
- [ ] push raster + polygon to geoserver.
- [x] spin this into it's own project on github.
- [ ] component diagram.

Later:

- [ ] MODIS + VIIRS as source. Current algorithm doesn't work with lots of cloud and smoke. Smoke may cause holes in the perimiter.

## General

- Create `.env` file (you can copy `.env.example` and set appropriate values)
- Assumes use of python poetry

## Ubuntu

```bash
pip install pygdal==3.0.4.10
```

## Using macports on m1

I had trouble using pyenv to install the version I need. So installing python with macports, and telling poetry to use the version I want.


```bash
sudo port selfupdate
sudo port upgrade outdated
sudo port install python38
sudo port install gdal
sudo port install proj9
```

Python 3.8 is installed to: /opt/local/Library/Frameworks/Python.framework/Versions/3.8

Find out where proj is installed, and set PROJ_DIR for your environment
```bash
port contents proj9
```

```bash
poetry env use /opt/local/Library/Frameworks/Python.framework/Versions/3.8/bin/python3
poetry run python -m pip install --upgrade pip
poetry install
poetry run python -m pip install gdal==$(gdal-config --version) --no-cache-dir
```

NOTE: --no-cache-dir is very important to make sure that gdal install doesn't skip numpy bindings.
NOTE: order is very important here, you need to have installed numpy before gdal.

## Openshift

### Build image
#### Shortcut!

Taking some shortcuts! Skipping build in openshift, and pushing up from local

```bash
make build
docker tag wps-fire-perimeter:latest image-registry.apps.silver.devops.gov.bc.ca/e1e498-tools/wps-fire-perimeter:latest
docker login -u developer -p $(oc whoami -t) image-registry.apps.silver.devops.gov.bc.ca
docker push image-registry.apps.silver.devops.gov.bc.ca/e1e498-tools/wps-fire-perimeter:latest
```

### Deployment

```bash
oc -n e1e498-dev process -f openshift/templates/perimeter_cronjob.yaml | oc -n e1e498-dev apply -f -
```

