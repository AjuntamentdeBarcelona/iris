from django.utils import timezone

from rest_framework import serializers


class HelloSerializer(serializers.Serializer):
    message = serializers.CharField(default='OK')
    current_time = serializers.DateTimeField(default=timezone.now)


class MeSerializer(serializers.Serializer):
    fullname = serializers.CharField(default='Anonymous User')
    user_id = serializers.CharField()
    username = serializers.CharField()
    email = serializers.CharField(default='')
    current_time = serializers.DateTimeField(default=timezone.now)
