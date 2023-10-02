from iris_masters.models import ApplicantType, Process, District, Reason, InputChannel, Support, Parameter


def load_missing_data_applicant():
    if not ApplicantType.objects.filter(id=0):
        applicant_type = ApplicantType(id=0)
        applicant_type.save()

    if not ApplicantType.objects.filter(id=1):
        applicant_type = ApplicantType(id=1)
        applicant_type.save()

    if not ApplicantType.objects.filter(id=23):
        applicant_type = ApplicantType(id=23)
        applicant_type.save()


def load_missing_data_process():
    if not Process.objects.filter(id=0):
        process = Process(id=0)
        process.save()

    if not Process.objects.filter(id=504):
        process = Process(id=504)
        process.save()

    if not Process.objects.filter(id=502):
        process = Process(id=502)
        process.save()

    if not Process.objects.filter(id=505):
        process = Process(id=505)
        process.save()


def load_missing_data_districts():
    for i in range(1, 12):
        if not District.objects.filter(id=i):
            if i == 11:
                district = District(id=i, name=f"District {i}", allow_derivation=False)
            else:
                district = District(id=i, name=f"District {i}")
            district.save()


def load_missing_data_reasons():
    if not Reason.objects.filter(id=700):
        reason = Reason(id=700)
        reason.save()

    if not Reason.objects.filter(id=1300):
        reason = Reason(id=1300)
        reason.save()

    if not Reason.objects.filter(id=1400):
        reason = Reason(id=1400)
        reason.save()

    if not Reason.objects.filter(id=1100):
        reason = Reason(id=1100)
        reason.save()

    if not Reason.objects.filter(id=12):
        reason = Reason(id=12)
        reason.save()

    if not Reason.objects.filter(id=90):
        reason = Reason(id=90)
        reason.save()

    if not Reason.objects.filter(id=91):
        reason = Reason(id=91)
        reason.save()

    if not Reason.objects.filter(id=1299):
        reason = Reason(id=1299)
        reason.save()

    if not Reason.objects.filter(id=25):
        reason = Reason(id=25)
        reason.save()

    if not Reason.objects.filter(id=900):
        reason = Reason(id=900)
        reason.save()

    if not Reason.objects.filter(id=0):
        reason = Reason(id=0, reason_type=Reason.TYPE_1)
        reason.save()

    if not Reason.objects.filter(id=19):
        reason = Reason(id=19)
        reason.save()

    if not Reason.objects.filter(id=26):
        reason = Reason(id=26, reason_type=Reason.TYPE_1)
        reason.save()

    if not Reason.objects.filter(id=17):
        reason = Reason(id=17, reason_type=Reason.TYPE_1)
        reason.save()

    if not Reason.objects.filter(id=1):
        reason = Reason(id=1, reason_type=Reason.TYPE_1)
        reason.save()


def load_missing_data_input():
    if not InputChannel.objects.filter(id=68):
        input_channel = InputChannel(id=68)
        input_channel.save()

    if not InputChannel.objects.filter(id=73):
        input_channel = InputChannel(id=73)
        input_channel.save()

    if not InputChannel.objects.filter(id=59):
        input_channel = InputChannel(id=59)
        input_channel.save()


def load_missing_data_support():
    if not Support.objects.filter(id=29):
        support = Support(id=29)
        support.save()

    if not Support.objects.filter(id=8):
        support = Support(id=8)
        support.save()

    if not Support.objects.filter(id=12):
        support = Support(id=12)
        support.save()


def load_missing_data_parameters():
    if not Parameter.objects.filter(parameter='TEXTCARTAFI'):
        param = Parameter(parameter='TEXTCARTAFI')
        param.save()

    if not Parameter.objects.filter(parameter='TEXTCARTAFI_CAST'):
        param = Parameter(parameter='TEXTCARTAFI_CAST')
        param.save()

    if not Parameter.objects.filter(parameter='TEXTCARTASIGNATURA'):
        param = Parameter(parameter='TEXTCARTASIGNATURA')
        param.save()

    if not Parameter.objects.filter(parameter='TEXTCARTASIGNATURA_CAST'):
        param = Parameter(parameter='TEXTCARTASIGNATURA_CAST')
        param.save()

    if not Parameter.objects.filter(parameter='PEU_CONSULTES_CAT'):
        param = Parameter(parameter='PEU_CONSULTES_CAT')
        param.save()

    if not Parameter.objects.filter(parameter='PEU_CONSULTES_CAST'):
        param = Parameter(parameter='PEU_CONSULTES_CAST')
        param.save()

