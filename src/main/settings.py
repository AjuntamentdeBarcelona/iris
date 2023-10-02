import logging
from copy import deepcopy
from kombu import Queue, Exchange

from configurations import Configuration
from corsheaders.defaults import default_headers
from django.contrib.messages import constants as messages
from django.core.files.storage import FileSystemStorage
from django.utils.translation import gettext_lazy
from django.conf import global_settings
from django.utils.module_loading import import_string

from main.auth_backends import AUTH_BACKENDS
from kaio import Options, mixins

opts = Options()

logger = logging.getLogger(__name__)


auth_mode = opts.get('AUTH_MODE')


def get_config_apps():
    """
    Gets a list of django apps from different configuration strategies.
    """
    return AUTH_BACKENDS.get(auth_mode, {}).get('apps', [])


def get_scheduled_tasks():
    """
    Gets a list of tasks to be scheduled from external module
    """
    schedule_backend = opts.get('SCHEDULE_BACKEND', 'main.schedules.scheduled_tasks')
    try:
        scheduled_tasks = import_string(schedule_backend)
        return scheduled_tasks()
    except ImportError:
        logger.info(f"Unable to locate the module {schedule_backend}, couldn't get external tasks.")

    return {}


class Base(mixins.CachesMixin, mixins.DatabasesMixin, mixins.CompressMixin,
           mixins.PathsMixin, mixins.LogsMixin, mixins.EmailMixin,
           mixins.SecurityMixin, mixins.DebugMixin, mixins.WhiteNoiseMixin,
           mixins.StorageMixin, Configuration):
    """
    Project settings for development and production.
    """

    DEBUG = opts.get("DEBUG", True)

    STATIC_URL = "/services/iris/static/"
    STATIC_ROOT = "/data/services/iris/static/"

    MEDIA_URL = "/services/iris/media/"

    AUTH_MODE = auth_mode
    BASE_DIR = opts.get("APP_ROOT", None)
    APP_SLUG = opts.get("APP_SLUG", "iris2-community")
    SITE_ID = 1
    INSTALLED_APPS = [
        # django
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "django.contrib.postgres",
        "django.contrib.gis",

        # apps
        "main",
        "iris_masters.apps.IrisMastersConfig",
        "ariadna.apps.AriadnaConfig",
        "communications.apps.CommunicationsConfig",
        "emails.apps.EmailsConfig",
        "features.apps.FeaturesConfig",
        "integrations.apps.IntegrationsConfig",
        "integrations.manual_task_schedule.apps.ManualTaskScheduleConfig",
        "profiles.apps.ProfilesConfig",
        "iris_templates.apps.IrisTemplatesConfig",
        "public_api.apps.PublicApiConfig",
        "public_external_processing.apps.PublicExternalProcessingConfig",
        "record_cards.apps.RecordCardsConfig",
        "reports.apps.ReportsConfig",
        "surveys.apps.SurveyConfig",
        "themes.apps.ThemesConfig",
        "protocols.apps.ProtocolsConfig",
        "quioscs.apps.QuioscsConfig",
        "support_info.apps.SupportInfoConfig",
        "post_migrate.apps.PostMigrateConfig",
        "geo",
        "geo_proxy.apps.GeoProxyConfig",

        # 3rd parties
        "drf_yasg",
        "modeltranslation",
        "compressor",
        "rest_framework",
        "rest_framework.authtoken",

        "django_filters",
        "constance",
        "constance.backends.database",
        "django_extensions",
        "django_yubin",
        "kaio",
        "logentry_admin",
        "robots",
        "storages",
        "corsheaders",
        "django_prometheus",
        "safedelete",
        "mptt",
        "solo",
        "django_celery_results",
        "cachalot",
        "minio_storage",
        "drf_chunked_upload",
        "django_celery_beat"
    ] + get_config_apps()
    SECRET_KEY = opts.get("SECRET_KEY", "key")

    USE_I18N = True
    USE_L10N = True
    USE_TZ = True
    LANGUAGE_CODE = "es"
    LANGUAGES = (
        ("es", gettext_lazy("Spanish")),
        ("gl", gettext_lazy("Galician")),
        ("en", gettext_lazy("English")),
    )
    MODELTRANSLATION_LANGUAGES = [l[0] for l in LANGUAGES]
    TIME_ZONE = "Europe/Madrid"

    ROOT_URLCONF = "main.urls"
    WSGI_APPLICATION = "main.wsgi.application"

    if DEBUG:
        INSTALLED_APPS += ["rosetta"]

    HEALTH_CHECK_APPS = [
        "health_check",
        "health_check.db",
        # stock Django health checkers
        "health_check.cache",
        # "health_check.storage",
        # "health_check.contrib.celery",
        # "health_check.contrib.s3boto_storage",
    ]

    INSTALLED_APPS += HEALTH_CHECK_APPS

    APPLICATION_HASH_SALT = "xo756OKR16268060"
    MESSAGE_HASH_SALT = "aFBk4D6579350001a"

    MIDDLEWARE = [
        "django_prometheus.middleware.PrometheusBeforeMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "django.middleware.locale.LocaleMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "corsheaders.middleware.CorsMiddleware",  # Django Cors Headers
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "django_prometheus.middleware.PrometheusAfterMiddleware",
        "main.middleware.ApplicationMiddelware",
    ]

    # SecurityMiddleware options
    SECURE_BROWSER_XSS_FILTER = True

    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [
                # insert additional TEMPLATE_DIRS here
            ],
            "OPTIONS": {
                "context_processors": [
                    "django.contrib.auth.context_processors.auth",
                    "django.template.context_processors.debug",
                    "django.template.context_processors.i18n",
                    "django.template.context_processors.media",
                    "django.template.context_processors.static",
                    "django.contrib.messages.context_processors.messages",
                    "django.template.context_processors.tz",
                    "django.template.context_processors.request",
                    "constance.context_processors.config",
                ],
                "loaders": [
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ]
            },
        },
    ]
    if not DEBUG:
        TEMPLATES[0]["OPTIONS"]["loaders"] = [
            ("django.template.loaders.cached.Loader", TEMPLATES[0]["OPTIONS"]["loaders"]),
        ]

    # Bootstrap 3 alerts integration with Django messages
    MESSAGE_TAGS = {
        messages.ERROR: "danger",
    }

    # Constance
    CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
    CONSTANCE_DATABASE_CACHE_BACKEND = "default"
    CONSTANCE_CONFIG = {
        "GOOGLE_ANALYTICS_TRACKING_CODE": ("UA-XXXXX-Y", "Google Analytics tracking code."),
    }
    TAGGIT_CASE_INSENSITIVE = True

    # Robots
    ROBOTS_SITEMAP_URLS = [opts.get("SITEMAP_URL", "")]
    AUTHENTICATION_BACKENDS = [
      'django.contrib.auth.backends.ModelBackend',
    ] + AUTH_BACKENDS.get(auth_mode, {}).get('auth_backends', [])

    # Rest frameworks
    REST_FRAMEWORK = {
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
            "drf_renderer_xlsx.renderers.XLSXRenderer",
        ],

        # Use Django's standard `django.contrib.auth` permissions,
        # or allow read-only access for unauthenticated users.
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        "DEFAULT_AUTHENTICATION_CLASSES": AUTH_BACKENDS.get(auth_mode, {}).get('rest_auth_backends', []),
        "DEFAULT_FILTER_BACKENDS": [
            "django_filters.rest_framework.DjangoFilterBackend"
        ],
        "DEFAULT_PAGINATION_CLASS": "main.api.pagination.IrisPagination",
        "PAGE_SIZE": 100,
    }

    if DEBUG:
        REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].append("rest_framework.authentication.SessionAuthentication")

    SWAGGER_SETTINGS = {
        "DEFAULT_AUTO_SCHEMA_CLASS": "main.open_api.inspectors.view.ExtendedSwaggerAutoSchema",
    }
    OPEN_API = {
        "DEFAULT_IMI_ROLE": {
            "admin": "Only admin user can access this operation"
        }
    }

    # Public API config
    PUBLIC_API_ACTIVE = opts.get("PUBLIC_API_ACTIVE", True)

    # Api connect integration data
    CLIENT_ID = opts.get("CLIENT_ID", "")
    CLIENT_SECRET = opts.get("CLIENT_SECRET", "")
    BASE_URL = opts.get('BASE_URL', '')

    AC_INTEGRATIONS = {
        "Geocod": [
            {"connectiontype": "publc api", "url": opts.get('URL_PA_GEO', '')},
            {"connectiontype": "apiconnect",
             "url": opts.get('URL_AC_GEO',
                             BASE_URL + '')}],

        "Georest": [
            {"connectiontype": "publc api", "url": opts.get('URL_PA_GEOREST', '')},
            {"connectiontype": "apiconnect",
             "url": opts.get('URL_AC_GEOREST',
                             BASE_URL + '')}],

        "Rat": [{"connectiontype": "public api", "url": opts.get('URL_PA_RAT', '')},
                {"connectiontype": "apiconnect",
                 "url": opts.get('URL_AC_RAT', BASE_URL + '')}],

        "Sms": [{"connectiontype": "public api", "url": opts.get('URL_PA_SMS', '')},
                {"connectiontype": "apiconnect",
                 "url": opts.get('URL_AC_SMS', BASE_URL + '')}],

        "Mario": [{"connectiontype": "public api", "url": opts.get('URL_PA_MARIO', '')},
                  {"connectiontype": "apiconnect",
                   "url": opts.get('URL_AC_MARIO', BASE_URL + '')}],

        "Mib": [{"connectiontype": "public api", "url": opts.get('URL_PA_MIB', '')},
                {"connectiontype": "apiconnect",
                 "url": opts.get('URL_AC_MIB', BASE_URL + '')}],

        "Idj": [{"connectiontype": "public api", "url": opts.get('URL_PA_IDJ', '')},
                {"connectiontype": "apiconnect",
                 "url": opts.get('URL_AC_IDJ', BASE_URL + '')}],


        "Twitter": [{"connectiontype": "public api", "url": opts.get('URL_PA_TWITTER', '')},
                    {"connectiontype": "apiconnect",
                     "url": opts.get('URL_AC_TWITTER', BASE_URL + '')}],
    }

    AC_HEADERS = {
        "X-IBM-Client-Id": CLIENT_ID,
        "X-IBM-Client-Secret": CLIENT_SECRET,
        "content-type": "application/json",
        "accept": "*/*"
    }

    IDJ_HEADERS = {
        "X-IBM-Client-Id": CLIENT_ID,
        "X-IBM-Client-Secret": CLIENT_SECRET,
        "content-type": "multipart/form-data",
        "accept": "application/octet-stream"
    }

    EXT_HEADERS = {
        "content-type": "application/json",
    }

    TWITTER_ACCESS_TOKEN = opts.get("TWITTER_ACCESS_TOKEN", "")
    TWITTER_TOKEN_SECRET = opts.get("TWITTER_TOKEN_SECRET", "")
    TWITTER_CONSUMER_KEY = opts.get("TWITTER_CONSUMER_KEY", "")
    TWITTER_CONSUMER_SECRET = opts.get("TWITTER_CONSUMER_SECRET", "")

    CITYOS_SERVER = opts.get('CITYOS_SERVER', '')
    CITYOS_TOPIC = opts.get('CITYOS_TOPIC', '')

    KEYTAB_PATH = opts.get('KEYTAB_PATH', '')
    KINIT_USER = opts.get('KINIT_USER', '')

    SFTP_HOSTNAME = opts.get('SFTP_HOSTNAME', '')
    SFTP_USERNAME = opts.get('SFTP_USERNAME', '')
    SFTP_PASSWORD = opts.get('SFTP_PASSWORD', '')
    SFTP_PATH = opts.get('SFTP_PATH', '')

    BI_FILE_PAGE = opts.get('BI_FILE_PAGE', '')

    AUT_CODI = opts.get('AUT_CODI', '')

    @property
    def COMPRESS_PRECOMPILERS(self):
        precompilers = []
        if self.COMPRESS_SASS_ENABLED:
            precompilers.append(("text/scss", self.COMPRESS_SASS_PATH + " {infile} {outfile}"))
        ROLLUP_PATH = opts.get("COMPRESS_ROLLUP_PATH", "../node_modules/.bin/rollup ")
        ROLLUP_CONFIG_PATH = opts.get("COMPRESS_ROLLUP_CONFIG_PATH", "../rollup.config.js")
        precompilers.append(("text/rollup", ROLLUP_PATH + " --config=" + ROLLUP_CONFIG_PATH + " {infile}"))
        return precompilers

    # Cors Headers
    CORS_ORIGIN_WHITELIST = (
        "localhost:3000",
        "localhost:8000",
        "localhost:8001",
        "127.0.0.1:3000",
        "127.0.0.1:8000",
        "127.0.0.1:8001",
    ) if DEBUG else opts.get('CORS_ORIGIN_WHITELIST', '').split(',')

    CORS_ALLOW_CREDENTIALS = True

    CORS_ALLOW_HEADERS = default_headers + (
        "X-IBM-Client-Id",
        "X-Username",
        "x-imi-authorization",
        "content-range",
        "x-imi-authorization",
    )

    CORS_EXPOSE_HEADERS = (
        "content-disposition",
    )

    # pgBouncer
    # https://docs.djangoproject.com/en/2.1/ref/databases/#transaction-pooling-server-side-cursors
    DISABLE_SERVER_SIDE_CURSORS = True

    # Prometheus
    PROMETHEUS_EXPORT_MIGRATIONS = False

    # APP_DOMAIM
    APP_DOMAIM = opts.get("APP_DOMAIM", "https://iris-int.ajuntament.bcn")

    # CITIZEN_ND
    CITIZEN_ND = "ND"
    CITIZEN_NDD = "NDD"
    CITIZEN_ND_ENABLED = opts.get("CITIZEN_ND_ENABLED", True)

    # Celery
    CELERY_ENABLE_UTC = opts.get("CELERY_ENABLE_UTC", False)
    CELERY_HIGH_QUEUE_NAME = "high_priority"
    CELERY_LOW_QUEUE_NAME = "low_priority"
    CELERY_CITYOS = "CITYOS"
    CELERY_REDIRECT_STDOUTS_LEVEL = opts.get("CELERY_REDIRECT_STDOUTS_LEVEL", "DEBUG")
    CELERY_BROKER_URL = opts.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/1")
    CELERY_IGNORE_RESULT = True
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_QUEUES = (
        Queue(CELERY_HIGH_QUEUE_NAME, Exchange(CELERY_HIGH_QUEUE_NAME), routing_key=CELERY_HIGH_QUEUE_NAME),
        Queue(CELERY_LOW_QUEUE_NAME, Exchange(CELERY_LOW_QUEUE_NAME), routing_key=CELERY_LOW_QUEUE_NAME),
        Queue(CELERY_CITYOS, Exchange(CELERY_CITYOS), routing_key=CELERY_CITYOS),
    )
    CELERY_TASK_ALWAYS_EAGER = opts.get("CELERY_TASK_ALWAYS_EAGER", False)

    # Celery crontabs
    CELERY_RESULT_BACKEND = "django-db"
    TASKS_SCHEDULE = get_scheduled_tasks()

    CELERY_BEAT_SCHEDULE = {}
    pop_task_keys = ["show_log", "user_retry"]
    for key_task, task in TASKS_SCHEDULE.items():
        new_task = deepcopy(task)
        for pop_key in pop_task_keys:
            new_task.pop(pop_key, None)
        CELERY_BEAT_SCHEDULE[key_task] = new_task

    SEND_MAIL_ACTIVE = opts.get("SEND_MAIL_ACTIVE", False)
    MAILER_TEST_MODE = opts.get('MAILER_TEST_MODE', False)
    MAILER_TEST_EMAIL = opts.get('MAILER_TEST_EMAIL', 'iris@bcn.cat')

    # SOLO CACHE
    SOLO_CACHE_TIMEOUT = 60 * 60  # 60 mins

    EXECUTE_DATA_CHEKS = opts.get('EXECUTE_DATA_CHEKS', False)

    def DATABASES(self):
        databases = super().get_databases()
        if self.USE_DB_PASSWORD_FILE:
            databases["default"]["PASSWORD"] = self.get_db_password_from_file()
        return databases

    @property
    def USE_DB_PASSWORD_FILE(self):
        return opts.get("USE_DB_PASSWORD_FILE", True)

    def get_db_password_from_file(self):
        """
        Only for Barcelona the password must be /etc/iris/postgresql-secret/psql-dbpass.
        """
        if self.USE_DB_PASSWORD_FILE:
            return self.get_secret_from_file("DB_PASSWORD_FILE", "/etc/iris/postgresql-secret/psql-dbpass")
        return None

    @property
    def EMAIL_HOST_PASSWORD(self):
        if self.USE_EMAIL_PASSWORD_FILE:
            return self.get_secret_from_file("EMAIL_HOST_PASSWORD_FILE", "/etc/iris/smtpcred/password")
        return opts.get("EMAIL_HOST_PASSWORD", "")

    @property
    def EMAIL_HOST_USER(self):
        if self.USE_EMAIL_PASSWORD_FILE:
            return self.get_secret_from_file("EMAIL_HOST_USER_FILE", "/etc/iris/smtpcred/username")
        return opts.get("EMAIL_HOST_USER", "")

    @property
    def DEFAULT_FROM_EMAIL(self):
        if self.USE_EMAIL_PASSWORD_FILE:
            return self.get_secret_from_file("DEFAULT_FROM_EMAIL_FILE", "/etc/iris/smtpcred/sender")
        return opts.get("DEFAULT_FROM_EMAIL", "")

    @property
    def USE_EMAIL_PASSWORD_FILE(self):
        return opts.get("USE_EMAIL_FILE_CREDENTIALS", False)

    DEFAULT_FILE_STORAGE = opts.get("DEFAULT_FILE_STORAGE", "main.storage.imi_minio_storage.IMIMinioMediaStorage")

    MINIO_HOST = opts.get("MINIO_HOST", "localhost")
    MINIO_PORT = opts.get("MINIO_PORT", 9000)
    MINIO_STORAGE_ENDPOINT = MINIO_HOST + (":" + str(MINIO_PORT) if MINIO_PORT else "")
    MINIO_STORAGE_MEDIA_BUCKET_NAME = opts.get("MINIO_BUCKET", "iris2")
    MINIO_STORAGE_IRIS1_MEDIA_BUCKET_NAME = opts.get("MINIO_BUCKET_IRIS1", "iris1")
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = opts.get("MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", True)
    MINIO_STORAGE_USE_HTTPS = opts.get("MINIO_SECURE", False)
    MINIO_MEDIA_URL_SECURE = opts.get("MINIO_MEDIA_URL_SECURE", MINIO_STORAGE_USE_HTTPS)
    MINIO_MEDIA_URL = opts.get("MINIO_MEDIA_URL", MINIO_STORAGE_ENDPOINT)
    MINIO_STORAGE_MEDIA_URL = "{}://{}/{}".format("https" if MINIO_MEDIA_URL_SECURE else "http", MINIO_MEDIA_URL,
                                                  MINIO_STORAGE_MEDIA_BUCKET_NAME)
    MINIO_STORAGE_MEDIA_USE_PRESIGNED = True
    USE_MINIO_SECRET_FILE = False
    MINIO_STORAGE_MEDIA_HIDE_DOMAIN = opts.get('MINIO_STORAGE_MEDIA_HIDE_DOMAIN', True)

    @property
    def DOWNLOAD_FILES_URL(self):
        res = opts.get("MINIO_MEDIA_URL", None)
        if res is not None:
            return 'https://' + res
        return 'http://localhost:8000'

    @property
    def MINIO_STORAGE_ACCESS_KEY(self):
        if self.USE_MINIO_SECRET_FILE:
            return self.get_secret_from_file("MINIO_ACCESS_KEY_FILE", "/etc/iris/minio-secret/accesskey")
        return opts.get("MINIO_ACCESS_KEY", "minioadmin")

    @property
    def MINIO_STORAGE_SECRET_KEY(self):
        if self.USE_MINIO_SECRET_FILE:
            return self.get_secret_from_file("MINIO_SECRET_KEY_FILE", "/etc/iris/minio-secret/secretkey")
        return opts.get("MINIO_SECRET_KEY", "minioadmin")

    def get_secret_from_file(self, opt_name, default_val):
        PASSWORD_FILE = opts.get(opt_name, default_val)
        try:
            with open(PASSWORD_FILE, "r") as pass_file:
                content = pass_file.read().strip()
                if not content:
                    raise Exception("SECRET file cannot be empty")
                return content
        except Exception:
            return None

    IRIS_CTRLUSER_APPNAME = opts.get("IRIS_CTRLUSER_APPNAME", "Iris2App")
    # Cachalot
    CACHALOT_TIMEOUT = 3600 * 8  # timeout of 8 hours

    CACHALOT_FEATURES_TABLES = ("features_feature", "features_mask", "features_values", "features_valuestype")
    CACHALOT_MASTERS_TABLES = ("iris_masters_announcement", "iris_masters_announcement_seen_by",
                               "iris_masters_applicanttype", "iris_masters_application",
                               "iris_masters_communicationmedia", "iris_masters_district",
                               "iris_masters_externalservice", "iris_masters_inputchannel",
                               "iris_masters_inputchannelapplicanttype", "iris_masters_inputchannelsupport",
                               "iris_masters_mediatype", "iris_masters_parameter", "iris_masters_process",
                               "iris_masters_reason", "iris_masters_recordstate", "iris_masters_recordtype",
                               "iris_masters_resolutiontype", "iris_masters_responsechannel",
                               "iris_masters_responsechannelsupport", "iris_masters_responsetype",
                               "iris_masters_support")
    CACHALOT_TEMPLATES_TABLES = ("iris_templates_iristemplate", "iris_templates_iristemplaterecordtypes")
    CACHALOT_PROTOCOLS_TABLES = ("protocols_protocol",)
    CACHALOT_PROFILES_TABLES = ("profiles_applicationgroup", "profiles_group", "profiles_groupdeleteregister",
                                "profiles_groupinputchannel", "profiles_groupprofiles", "profiles_usergroup",
                                "profiles_groupreassignation", "profiles_permission", "profiles_permissioncategory",
                                "profiles_profile", "profiles_profilepermissions")
    CACHALOT_THEMES_TABLES = ("themes_applicationelementdetail", "themes_area", "themes_derivationdirect",
                              "themes_derivationdistrict", "themes_element", "themes_elementdetail",
                              "themes_elementdetail_response_channels", "themes_elementdetailfeature",
                              "themes_elementdetailgroup", "themes_elementdetailthemegroup", "themes_keyword",
                              "themes_themegroup")
    CACHALOT_SURVEYS_TABLES = ("surveys_question", "surveys_questionreason", "surveys_survey")
    CACHALOT_SUPPORT_INFO_TABLES = ("support_info_supportinfo",)

    CACHALOT_ONLY_CACHABLE_TABLES = CACHALOT_FEATURES_TABLES + CACHALOT_MASTERS_TABLES + CACHALOT_TEMPLATES_TABLES
    CACHALOT_ONLY_CACHABLE_TABLES += CACHALOT_PROTOCOLS_TABLES + CACHALOT_PROFILES_TABLES + CACHALOT_THEMES_TABLES
    CACHALOT_ONLY_CACHABLE_TABLES += CACHALOT_SURVEYS_TABLES + CACHALOT_SUPPORT_INFO_TABLES

    # Chuncked Files
    DRF_CHUNKED_UPLOAD_PATH = opts.get("DRF_CHUNKED_UPLOAD_PATH", "record_files/%Y/%m/%d/")
    DRF_CHUNKED_UPLOAD_MAX_BYTES = opts.get("DRF_CHUNKED_UPLOAD_MAX_BYTES", 10485760)  # 10MB
    DRF_CHUNKED_UPLOAD_ABSTRACT_MODEL = True
    # Acumulate chunks on the same part
    DRF_CHUNKED_UPLOAD_INCOMPLETE_EXT = '.done'

    # Setting to choose the system of groups used
    INTERNAL_GROUPS_SYSTEM = opts.get("INTERNAL_GROUPS_SYSTEM", True)
    DEFAULT_ADMIN = opts.get("DEFAULT_ADMIN_USER", "ADMIN")
    DEFAULT_ADMIN_PASSWORD = opts.get("DEFAULT_ADMIN_PASSWORD", "1234")
    SET_DEFAULT_ADMIN_BACKEND = opts.get(
        "SET_DEFAULT_ADMIN_BACKEND", "profiles.data_checks.default_admin.set_default_admin"
    )
    SET_AMBIT_COORDINATORS_BACKEND = opts.get(
        "SET_AMBIT_COORDINATORS_BACKEND", "profiles.data_checks.default_admin.set_ambit_coordinators"
    )
    SET_GROUP_PLATES_BACKEND = opts.get(
        "SET_GROUP_PLATES_BACKEND", "profiles.data_checks.group_plates.set_group_plates"
    )

    # Master could be public accessed if this flag is set, this way authorization is not checked since they are
    # Simple get calls

    OAUTH_AUTHORIZATION_URL = opts.get('OAUTH_AUTHORIZATION_URL')
    OAUTH_ACCESS_TOKEN_URL = opts.get('OAUTH_ACCESS_TOKEN_URL')
    OAUTH_USER_INFO_URL = opts.get('OAUTH_USER_INFO_URL')
    OAUTH_REDIRECT_LOGIN_URL = opts.get('OAUTH_REDIRECT_LOGIN_URL')

    MAX_FILE_SIZE_GROUP_ICON = opts.get("MAX_FILE_SIZE_GROUP_ICON", 1048576)  # 1MB
    POLYGON_GEO_BCN = opts.get("POLYGON_GEO_BCN", True)
    SOCIAL_AUTH_IRIS_OIDC_KEY = opts.get('OIDC_KEY', 'iris2-test')
    SOCIAL_AUTH_IRIS_OIDC_SECRET = opts.get('OIDC_SECRET', 'JsTNXo1pObCuPqnFXK7FqQc_f7Qa')
    SOCIAL_AUTH_PIPELINE = (
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.auth_allowed',
        # Associates the current social details with another username
        'main.oauth.pipeline.associate_by_username',
        'social_core.pipeline.social_auth.social_user',
        # Create a user account if we haven't found one yet.
        'social_core.pipeline.user.create_user',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
        'social_core.pipeline.user.user_details',
    )
    ENABLE_CITY_OS = opts.get('CITY_OS_ENABLED', False)

    # GEO
    GEO_UTM_ZONE = opts.get('UTM_ZONE', 29)
    GEO_SRID = opts.get('GEO_SRID', 25829)
    GEOCODER_SERVICES_CLASS = opts.get('GEOCODER_SERVICES_CLASS', '')
    GEOCODER_CLASS = opts.get('GEOCODER_CLASS', 'geo.geocode.GisGeocoder')

    # Integration tasks variables

    LETTER_RESPONSE_ENABLED = opts.get('LETTER_RESPONSE_ENABLED', False)
    PDF_BACKEND = opts.get('PDF_BACKEND', 'integrations.services.pdf.hooks.create_pdf')  # Change to none when tested
    MARIO_ENABLED = bool(opts.get('URL_PA_MARIO', ''))
    TWITTER_ENABLED = bool(opts.get('URL_PA_TWITTER', ''))
    TWITTER_BACKEND = opts.get('TWITTER_BACKEND', 'integrations.services.twitter.hooks.send_direct_message')
    SMS_BACKEND = opts.get('SMS_BACKEND', None)
    SMS_BACKEND_PENDENTS = opts.get('SMS_BACKEND_PENDENTS', None)

    # GeoProxy App variables (ordered by search order)
    POSTAL_CODE = opts.get('POSTAL_CODE', '')
    CITY = opts.get('CITY', '')
    COUNTY = opts.get('COUNTY', '')  # Provincia
    STATE = opts.get('STATE', '')  # Comunidad Autónoma
    COUNTRY = opts.get('COUNTRY', '')
    # Viewbox param for nominatim https://nominatim.org/release-docs/latest/api/Search/#result-limitation
    GEO_VIEWBOX = opts.get('GEO_VIEWBOX', '43.395024,-8.472844,43.301379,%20-8.380706')

    # GeoProxy App list generators VARIABLES

    STREET_TYPE_MAP_GENERATOR = opts.get('STREET_TYPE_MAP_GENERATOR', 'geo_proxy.maps.street_types.generate_list')
    IGNORED_KEYS_LIST_GENERATOR = opts.get('IGNORED_KEYS_LIST_GENERATOR', 'geo_proxy.address.ignored_keys.generate_list')
    STREET_TYPE_TRANSLATION_LANGUAGE_CODE = opts.get('STREET_TYPE_TRANSLATION_LANGUAGE_CODE', '')

    # Date accepted formats
    DATE_INPUT_FORMATS = [
        "%d/%m/%Y",
    ]


class Test(Base):
    """
    Project settings for testing.
    """
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_ROOT = opts.get("TEST_MEDIA_ROOT", "/tmp/iris2-media_test")

    CACHE_PREFIX = "iris2-test"
    CACHE_TYPE = 'dummy'

    EMAIL_HOST = "smtp.sendgrid.net"
    EMAIL_PORT = 587
    EMAIL_HOST_USER = opts.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = opts.get("EMAIL_HOST_PASS", "")
    EMAIL_USE_TLS = True

    CELERY_BROKER_URL = "memory://"

    INTERNAL_GROUPS_SYSTEM = True

    POLYGON_GEO_BCN = False

    EXECUTE_DATA_CHEKS = False

    DEFAULT_ADMIN = False

    def DRF_CHUNKED_UPLOAD_STORAGE_CLASS(self):
        return FileSystemStorage  # noqa E731

    @property
    def USE_DB_PASSWORD_FILE(self):
        return opts.get("USE_DB_PASSWORD_FILE", False)

    def DATABASES(self):
        databases = self.get_databases(prefix="TEST_")
        databases['default']['NAME'] = opts.get('TEST_DATABASE_NAME', ':memory:')
        return databases
