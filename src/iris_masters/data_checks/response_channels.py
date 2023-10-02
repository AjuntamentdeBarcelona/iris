from iris_masters.models import ResponseChannel

from django.utils.translation import gettext_lazy as _


def check_response_channels(sender, **kwargs):
    response_types = {
        ResponseChannel.EMAIL: {'name': _(u"Email"), 'order': 0},
        ResponseChannel.LETTER: {'name': _(u"Letter"), 'order': 1},
        ResponseChannel.SMS: {'name': _(u"Sms"), 'order': 2},
        ResponseChannel.NONE: {'name': _(u"None"), 'order': 3},
        ResponseChannel.TELEPHONE: {'name': _(u"Telephone"), 'order': 4},
        ResponseChannel.IMMEDIATE: {'name': _(u"Immediate"), 'order': 5},
    }

    for (response_channel_key, response_channel_data) in response_types.items():
        response_channel, created = ResponseChannel.objects.get_or_create(
            id=response_channel_key,
            defaults={'name': response_channel_data['name'], 'order': response_channel_data['order']})
        if not created and response_channel.order == 100:
            response_channel.order = response_channel_data['order']
            response_channel.save()
