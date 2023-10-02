from iris_masters.models import Application, RecordState, ResponseChannel


def load_missing_data():
    for i in range(0, 10):
        if not ResponseChannel.objects.filter(id=i):
            response_channel = ResponseChannel(id=i)
            response_channel.save()

    if not Application.objects.filter(id=0):
        application = Application(id=0)
        application.save()

    for i in range(0, 10):
        if not RecordState.objects.filter(id=i):
            record_state = RecordState(id=i)
            record_state.save()
