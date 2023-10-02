EXECUTED_OK = 'OK'


def dummy_task_with_kwargs(test_kwarg=False):
    """
    Dummy task for testing if an schedule task is passing correctly the kwargs to the task that has to be executed.
    :param test_kwarg:
    :return: True of the parameter has arrived to the task
    """
    if not test_kwarg:
        raise Exception("Task is not receiving kwargs")
