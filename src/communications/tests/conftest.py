import uuid

import py
import pytest
import os

from django.conf import settings


@pytest.fixture()
def test_file():
    if not os.path.exists(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    file = py.path.local(settings.MEDIA_ROOT).join("{}.txt".format(str(uuid.uuid4())[:10]))
    file.write("content")
    return open(file)
