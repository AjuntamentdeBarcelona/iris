all: devel

devel:
	docker-compose build devel
	docker-compose run --rm --service-ports devel python manage.py diffsettings
	docker-compose run --service-ports --rm devel

migrate:
	docker-compose run --rm devel python manage.py migrate

manage:
	docker-compose run --rm --service-ports devel python manage.py ${c}

uwsgi:
	docker-compose build uwsgi
	docker-compose run --service-ports --rm uwsgi

.PHONY: devel manage migrate
