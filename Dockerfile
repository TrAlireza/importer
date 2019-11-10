FROM python:3-alpine
RUN apk add --no-cache bash curl zip

WORKDIR /opt/ometria

RUN mkdir -p /opt/ometria/importer /opt/ometria/tests /opt/ometria/lib /opt/ometria/state

COPY requirements.txt .
RUN pip install -r requirements.txt

ENTRYPOINT ["docker-entrypoint.sh"]
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

COPY lib/*.py /opt/ometria/lib/
COPY importer/*.py /opt/ometria/importer/
COPY tests /opt/ometria/tests
COPY state/*.json /opt/ometria/state/
