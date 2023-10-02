#!/bin/bash

set -e

case $1 in
    run-uwsgi)
        # python manage.py compilemessages
        # force for temporary always launch migrations
        python manage.py diffsettings
        python manage.py migrate --noinput

        if [ "${ENABLE_BASIC_AUTH}" = "True" ]; then
            echo "→ Enable basic auth"
            sed -i -e "s/##ENABLE_BASIC_AUTH //g" /etc/uwsgi/uwsgi.ini
        else
            echo "→ Running in clear (non auth) mode"
        fi
        exec uwsgi --ini=/etc/uwsgi/uwsgi.ini
        ;;

    run-migrations)
        /entrypoint.sh launch-migrations
        exec sleep infinity
        ;;

    run-crons)
        echo "→ Starting cron"
        exec go-cron -v -cmd-prefix "python manage.py" -file /etc/crons.yml
        ;;

    run-uwsgitop)
        exec uwsgitop localhost:9090
        ;;

    run-devel)
        if [ ! -e /app/app.ini ]; then
            cp /srv/app.ini /app/app.ini
        fi
        chmod 666 /app/app.ini
        /entrypoint.sh launch-migrations
        echo "→ Running as runserver mode"
        exec python manage.py runserver 0.0.0.0:8000
        ;;

    launch-migrations)
        echo "→ Executing migrate"
        exec python manage.py migrate --noinput
        echo "✓ Migrations applied"
        ;;

    run-tests)
        cd /srv
        pipenv install --system --dev
        cd /app
        pytest --create-db --migrations
        ;;

    launch-liveness-probe)
        exec curl -f localhost:8080/health/ || exit 1
        ;;

    launch-readiness-probe)
        exec python manage.py showmigrations | grep -c "\[ \]" -m 1 | grep -q 0 || exit 1
        ;;

    run-celery)
        exec celery worker -A main.celery  -l info -E -Q high_priority,low_priority
        ;;

    run-beat)
        exec celery beat -A main.celery -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --pidfile="/tmp/celerybeat.pid" & celery flower -A main.celery -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --pidfile="/tmp/celerybeat.pid"
        ;;

    launch-celery-liveness-probe)
        exec celery inspect -t ${CELERY_INSPECT_TIMEOUT} ping -A main.celery || exit 1
        ;;


    *)
        exec "$@"
        ;;
esac
