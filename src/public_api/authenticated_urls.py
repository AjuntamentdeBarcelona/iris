"""
PUBLIC API - AUTHENTICATED URLS

This file defines which urls can be accessed from internet requiring login.
As has been explained, with "public" we mean that this API can be accessed from the internet. The module exposes two
kinds of urls, those that full public (no-auth) and those which require a user.
"""
from django.urls import path, include

urlpatterns = [
    path('management/', include(('public_external_processing.urls', 'public_external_processing'),
                                namespace='public_external_processing_management')),
    path('', include(('public_external_processing.urls', 'public_external_processing'),
                     namespace='public_external_processing')),
]
