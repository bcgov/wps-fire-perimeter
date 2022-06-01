```bash
make build
docker tag wps-server-raster:latest image-registry.apps.silver.devops.gov.bc.ca/e1e498-tools/wps-server-raster:latest
docker login -u developer -p $(oc whoami -t) image-registry.apps.silver.devops.gov.bc.ca
docker push image-registry.apps.silver.devops.gov.bc.ca/e1e498-tools/wps-server-raster:latest
```

```bash
oc -n e1e498-dev process -f openshift/rasterserv/rasterserv.yaml | oc -n e1e498-dev apply -f -
```
