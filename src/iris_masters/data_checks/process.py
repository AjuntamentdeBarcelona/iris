from iris_masters.models import Process


def check_processes(sender, **kwargs):
    for (process_type_key, _) in Process.TYPES:
        _, _ = Process.objects.get_or_create(id=process_type_key)
