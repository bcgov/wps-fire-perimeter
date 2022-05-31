# Fire Boundaries using Google Earth Engine

[![Lifecycle:Experimental](https://img.shields.io/badge/Lifecycle-Experimental-339999)](https://github.com/bcgov/repomountie/blob/master/doc/lifecycle-badges.md)

Google Earth Engine does not work on versions newer than 3.8.*

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

