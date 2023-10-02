# https://hub.docker.com/r/library/nginx/tags/
FROM nginx:1.13.11-alpine

ENV ENABLE_BASIC_AUTH=False \
    ENABLE_HTTPS_REDIRECT=False \
    ENABLE_3W_REDIRECT=False \
    UWSGI_ADDR=

RUN rm /etc/nginx/conf.d/*
COPY htpasswd nginx.conf proxy_params /etc/nginx/
COPY entrypoint.sh /

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx-daemon"]
