from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.utils.translation import ugettext_lazy as _
from django.views.generic import RedirectView
from rest_framework.authtoken.views import obtain_auth_token

from main.auth_backends import get_plugin_urls
from main.iris_open_api import schema_view
from main.views import CeleryTestTask, InvalidateCache
from public_api.public_open_api import public_schema_view
from public_api.public_authenticated_open_api import public_auth_schema_view

admin.site.site_header = _("iris2-community Administration")
admin.site.site_title = _("iris2-community Admin")

BASE_PATH = 'services/iris/'
OPEN_API_BASE_PATH = BASE_PATH + 'api/'
PUBLIC_API_BASE_PATH = BASE_PATH + 'api-public/'
PUBLIC_AUTH_API_BASE_PATH = BASE_PATH + 'api-internet/'

OPEN_API_URL_NAME = 'schema-redoc'
PUBLIC_API_URL_NAME = 'public-schema-redoc'
PUBLIC_AUTH_API_URL_NAME = 'public-auth-schema-redoc'

urlpatterns = [
    path(BASE_PATH, RedirectView.as_view(url=f'/{OPEN_API_BASE_PATH}'), name='home'),
    path(f'health/', include('health_check.urls')),
    path(f'yubin/', include('django_yubin.urls')),
    path(f'{BASE_PATH}robots.txt', include('robots.urls')),
    path(f'{BASE_PATH}admin/', admin.site.urls),

    path(f'{BASE_PATH}api/test-task/', CeleryTestTask.as_view()),
    path(f'{BASE_PATH}api/invalidate-cache/', InvalidateCache.as_view()),

    path(f'{OPEN_API_BASE_PATH}token-auth/', obtain_auth_token),
    re_path(r'^{}swagger(?P<format>\.json|\.yaml)$'.format(OPEN_API_BASE_PATH),
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path(f'{OPEN_API_BASE_PATH}swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    path(f'{OPEN_API_BASE_PATH}', schema_view.with_ui('redoc', cache_timeout=0), name=OPEN_API_URL_NAME),
    path(f'{OPEN_API_BASE_PATH}', include(('main.urls_iris_api', 'private_api'))),
    path('', include('django_prometheus.urls')),
]

try:
    urlpatterns += get_plugin_urls(OPEN_API_BASE_PATH, getattr(settings, 'AUTH_MODE', None))
except KeyError:
    pass


if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [
        path(f'{BASE_PATH}admin/rosetta/', include('rosetta.urls'))
    ]

if settings.PUBLIC_API_ACTIVE:
    urlpatterns += [
        path(f'{PUBLIC_API_BASE_PATH}', public_schema_view.with_ui('redoc', cache_timeout=0), name=PUBLIC_API_URL_NAME),

        re_path(r'^{}swagger(?P<format>\.json|\.yaml)$'.format(PUBLIC_API_BASE_PATH),
                public_schema_view.without_ui(cache_timeout=0), name='public-schema-json'),
        path(f'{PUBLIC_API_BASE_PATH}swagger/', public_schema_view.with_ui('swagger', cache_timeout=10000),
             name='public_api-schema-swagger-ui'),

        path(f'{PUBLIC_API_BASE_PATH}', include(('public_api.urls', 'public_api'))),

        path(f'{PUBLIC_AUTH_API_BASE_PATH}', public_auth_schema_view.with_ui('redoc', cache_timeout=10000),
             name=PUBLIC_AUTH_API_URL_NAME),
        re_path(r'^{}swagger(?P<format>\.json|\.yaml)$'.format(PUBLIC_AUTH_API_BASE_PATH),
                public_auth_schema_view.without_ui(cache_timeout=0), name='public-schema-auth-json'),
        path(f'{PUBLIC_AUTH_API_BASE_PATH}swagger/', public_auth_schema_view.with_ui('swagger', cache_timeout=10000),
             name='public_api_auth_schema_swagger_ui'),
        path(f'{PUBLIC_AUTH_API_BASE_PATH}', include(('public_api.authenticated_urls', 'public_api_private'))),
    ]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    if settings.ENABLE_DEBUG_TOOLBAR:
        import debug_toolbar

        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
