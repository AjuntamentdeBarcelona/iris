from rest_framework import serializers

from main.api.validators import WordsLengthValidator


class ExternalProcessedSerializer(serializers.Serializer):

    comment = serializers.CharField(validators=[WordsLengthValidator(words=2, words_length=4)])
