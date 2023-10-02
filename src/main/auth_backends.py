from django.urls import path, include


AUTH_BACKENDS = {
    'oam': {
        'apps': [],
        'rest_auth_backends': [
            'profiles.authentication.OAMAuthentication'
        ],
        'auth_backends': [],
        'urls': {},
    },
    'oauth': {
        'apps': ['social_django', 'rest_social_auth'],
        'rest_auth_backends': [
            'main.oauth.authentication.IrisTokenAuthentication'
        ],
        'auth_backends': [
            'social_core.backends.open_id.OpenIdAuth',
            'main.oauth.backends.IrisOpenIdConnect',

        ],
        'urls': {
            'social/': 'social_django.urls',
            'oauth/': 'main.oauth.urls',
        }
    }
}


def get_auth_config(auth_model):
    return AUTH_BACKENDS[auth_model]


def get_plugin_urls(base_path, plugin_name):
    return [
        path(base_path + prefix, include(url_import))
        for prefix, url_import in AUTH_BACKENDS[plugin_name]['urls'].items()
    ]
