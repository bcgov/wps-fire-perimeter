
https://hub.docker.com/r/pramsey/pg_featureserv

docker run -dt -e DATABASE_URL=postgresql://user:pass@host/dbname -p 9000:9000 pramsey/pg_featureserv:latest