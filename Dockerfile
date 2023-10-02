FROM python:3.7.4-slim as builder
ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && xargs apt-get install -y --no-install-recommends build-essential \
    && apt-get clean -y \
    && apt-get autoremove -y \
    && rm -rf /tmp/* /var/tmp/* \
    && rm -rf /var/lib/apt/lists/*

COPY requirements /requirements/

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive xargs apt-get install -y --no-install-recommends < /requirements/system-dev.txt \
    && apt-get clean -y \
    && apt-get autoremove -y \
    && rm -rf /tmp/* /var/tmp/* \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /wheels/
RUN pip install -U pip \
    && pip install importlib-metadata==2.0.0 \
    && pip wheel -r /requirements/dev.txt -w /wheels
## Test step
FROM builder as tester
RUN pip install pytest pytest-cov

RUN pip install --no-cache-dir \
                -r /requirements/dev.txt \
                -f /wheels

COPY src/ /src/
COPY src/setup.cfg .

## Release image
FROM python:3.7.4-slim
ENV PYTHONUNBUFFERED=1

# Install system dependencies
COPY --from=builder /requirements /requirements
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive xargs apt-get install -y --no-install-recommends < /requirements/system-production.txt \
    && apt-get clean -y \
    && apt-get autoremove -y \
    && rm -rf /tmp/* /var/tmp/* \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY --from=builder /wheels /wheels
RUN pip install -U pip \
    && pip install --no-cache-dir \
                -r /requirements/production.txt \
                -f /wheels \
    && rm -rf /requirements /wheels

# Create user and group
RUN groupadd --system django \
    && useradd --system -g django django

# Add configuration
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh
COPY docker/app.docker.ini /app/app.ini
COPY docker/uwsgi.ini /etc/uwsgi/uwsgi.ini

## kinit configuration
#COPY docker/kinit/krb5.conf /etc/krb5.conf
#COPY docker/kinit/iris_pre.keytab /home/iris_pre.keytab

# Add application sources
WORKDIR /app
COPY src/ .
COPY docker/app.docker.ini /srv/app.ini
COPY docker/app.docker.ini /app/app.ini
COPY docker/uwsgi.ini /etc/uwsgi/uwsgi.ini
RUN chown -R django /app

RUN mkdir -p /app/main/static && cd /app/main/static/ && cd /app

ENTRYPOINT ["/entrypoint.sh"]
CMD ["run-uwsgi"]
EXPOSE 8080 1717

HEALTHCHECK --interval=30s --timeout=3s \
            CMD launch-probe

RUN mkdir -p app/data/static && mkdir -p app/data/media && \
    echo "Compiling messages..." && \
    CACHE_TYPE=dummy SECRET_KEY=iris2-community python manage.py compilemessages && \
    echo "Collecting statics..." && \
    CACHE_TYPE=dummy SECRET_KEY=iris2-community python manage.py collectstatic --noinput --traceback -v 0 && \
    chmod -R 777 app/data/ && \
    chmod -R 777 /etc/uwsgi

VOLUME /data/static
