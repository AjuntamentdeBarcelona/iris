from rest_framework import serializers


class SocialSerializer(serializers.Serializer):
    """
    Serializer which accepts an OAuth2 access token.
    """
    code = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )
