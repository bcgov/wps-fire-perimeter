# Notes

https://hub.docker.com/r/pramsey/pg_featureserv

## postgresql running on localhost, needs --network="host"

I run it this way on local:

```bash
docker run --network="host" -t -e DATABASE_URL=postgresql://user:pass@host/dbname -p 9000:9000 pramsey/pg_featureserv:latest
```

Example from https://hub.docker.com/r/pramsey/pg_featureserv:

```bash
docker run -dt -e DATABASE_URL=postgresql://user:pass@host/dbname -p 9000:9000 pramsey/pg_featureserv:latest
```

## Prepare your openshift environment

### Put image in place

```bash
# we have docker limits, so pull the pg_featureserv images locally - then put them in openshift

# pull local
docker pull pramsey/pg_featureserv

# tag for upload
docker tag pramsey/pg_featureserv image-registry.apps.silver.devops.gov.bc.ca/e1e498-tools/pg_featureserv:latest

# log in to openshift docker
docker login -u developer -p $(oc whoami -t) image-registry.apps.silver.devops.gov.bc.ca

# push it
docker push image-registry.apps.silver.devops.gov.bc.ca/e1e498-tools/pg_featureserv:latest

```

### Prepare database

Piggybacking off an existin database server, so

```bash
oc rsh existing-server
create user featureserv with password 'blah';
create database featureserv owner featureserv;
\c featureserv;
create extension postgis;
```

### Deploy pg_featureserv

```bash
# deploy pg_tileserv
oc -n e1e498-dev process -f featureserv.yaml | oc -n e1e498-dev apply -f -
```