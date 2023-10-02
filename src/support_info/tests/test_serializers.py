import pytest
from django.core.files.base import ContentFile
from model_mommy import mommy

from support_info.models import SupportInfo
from support_info.serializers import SupportInfoSerializer, SupportChunkedFileSerializer


class TestSupportInfoSerializer:

    @pytest.mark.parametrize("title,description,link,valid", (
            ("test", "description", "https://test.com", True),
            ("", "description", "https://test.com", False),
            ("test", "", "https://test.com", False),
            ("test", "description", "asdadsa", False),
    ))
    def test_basic_fields(self, title, description, link, valid):
        data = {
            "title": title,
            "description": description,
            "type": SupportInfo.VIDEO,
            "category": None,
            "file": None,
            "link": link
        }
        ser = SupportInfoSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("support_type,valid", (
            (SupportInfo.FAQS, True), (SupportInfo.GLOSSARY, True), (SupportInfo.DOCUMENTATION, True),
            (SupportInfo.VIDEO, True), (SupportInfo.NEWS, True), (110, False),
    ))
    def test_types(self, support_type, valid):
        data = {
            "title": "test",
            "description": "description",
            "type": support_type,
            "category": None,
            "file": None,
            "link": ""
        }
        ser = SupportInfoSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("category,valid", (
            (SupportInfo.TRAINING_COURSES, True), (SupportInfo.DAIQ_REPORTS, True), (SupportInfo.USER_MANUALS, True),
            (SupportInfo.REGULATIONS, True), (SupportInfo.LINKS, True), (SupportInfo.OTHERS, True), (110, False),
    ))
    def test_categories(self, category, valid):
        data = {
            "title": "test",
            "description": "description",
            "type": SupportInfo.DOCUMENTATION,
            "category": category,
            "file": None,
            "link": ""
        }
        ser = SupportInfoSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestSupportChunkedFileSerializer:

    @pytest.mark.parametrize("create_support,support_type,filename,valid", (
            (True, SupportInfo.DOCUMENTATION, "file.pdf", True),
            (False, SupportInfo.DOCUMENTATION, "file.pdf", False),
            (True, SupportInfo.FAQS, "file.pdf", False),
            (True, SupportInfo.DOCUMENTATION, "", False),
    ))
    def test_support_chuncked_file_serializer(self, base64_pdf, create_support, support_type, filename, valid):
        data = {"filename": filename}
        if create_support:
            data["support_info_id"] = mommy.make(
                SupportInfo, user_id="2222", type=support_type, file=None).pk
        chunk_size = 64 * 2 ** 5  # 2048 bytes
        data["file"] = ContentFile(base64_pdf[:chunk_size], name=filename)

        ser = SupportChunkedFileSerializer(data=data)
        assert ser.is_valid() is valid, "Support Chuncked file serializer fails"
        assert isinstance(ser.errors, dict)
