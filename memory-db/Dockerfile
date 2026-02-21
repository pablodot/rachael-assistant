FROM postgres:16-alpine

ENV POSTGRES_DB=rachael
ENV POSTGRES_USER=rachael
ENV POSTGRES_PASSWORD=rachael

# Init scripts run alphabetically on first container start
COPY init.sql /docker-entrypoint-initdb.d/01_init.sql
COPY seed.sql /docker-entrypoint-initdb.d/02_seed.sql
