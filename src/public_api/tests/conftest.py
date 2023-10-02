import pytest
import uuid

import py
import os

from django.conf import settings
from PIL import Image


@pytest.fixture(scope="session")
def image_file(tmpdir_factory):
    img = Image.new('RGB', (600, 300), color=(73, 109, 137))
    fn = tmpdir_factory.mktemp("data").join("img.png")
    img.save(str(fn))
    return img


@pytest.fixture()
def test_file():
    if not os.path.exists(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    file = py.path.local(settings.MEDIA_ROOT).join("{}.txt".format(str(uuid.uuid4())[:10]))
    file.write("content")
    return open(file)
