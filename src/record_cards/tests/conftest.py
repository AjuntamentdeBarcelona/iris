import pytest
from PIL import Image


@pytest.fixture(scope="session")
def image_file(tmpdir_factory):
    img = Image.new('RGB', (600, 300), color=(73, 109, 137))
    fn = tmpdir_factory.mktemp("data").join("img.png")
    img.save(str(fn))
    return img


@pytest.fixture()
def test_file(tmpdir):
    file = tmpdir.mkdir("sub").join("hello.txt")
    file.write("content")
    return open(file)
