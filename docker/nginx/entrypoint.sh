#!/bin/sh
set -e

# substitute the uwsgi address (for docker compose or using sockets)
if [ "${UWSGI_ADDR}" != "" ]; then
    echo "substituting uwsgi address for ${UWSGI_ADDR}"
    sed -i -e "s/server 127.0.0.1:8000/server ${UWSGI_ADDR}/g" /etc/nginx/nginx.conf
else
    echo "keep uwsgi default address"
fi

if [ "${ENABLE_BASIC_AUTH}" = "True" ]; then
    echo "Enable auth file"
    sed -i -e "s/#ENABLE_BASIC_AUTH //g" /etc/nginx/nginx.conf
fi

# Allow to force HTTP redirects
if [ "${ENABLE_HTTPS_REDIRECT}" = "True" ]; then
    echo "Enable HTTP force for the /"
    sed -i -e "s/#ENABLE_HTTPS_REDIRECT //g" /etc/nginx/nginx.conf
fi

if [ "${ENABLE_3W_REDIRECT}" == "True" ]; then
    echo "force www redirects "
    sed -i -e "s/#ENABLE_3W_REDIRECT //g" /etc/nginx/nginx.conf
else
    echo "www redirect will not be forced"
fi

if [ "$1" = 'nginx-daemon' ]; then
    echo "Starting up"
    cat -n /etc/nginx/nginx.conf
    exec nginx -g "daemon off;";
fi

exec "$@"
