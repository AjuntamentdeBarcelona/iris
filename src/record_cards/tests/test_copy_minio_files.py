import pytest
from mock import Mock, patch

from iris_masters.models import Reason
from main.storage.imi_minio_storage import IMIMinioMediaStorage
from record_cards.models import RecordFile, Comment
from record_cards.record_actions.copy_minio_files import CopyMinioFiles
from record_cards.tests.utils import CreateRecordCardMixin


class DummyStorage(IMIMinioMediaStorage):

    def __init__(self, bucket_name):
        super().__init__()
        self.bucket_name = bucket_name


@pytest.mark.django_db
class TestCopyMinioFiles(CreateRecordCardMixin):

    def test_copy_minio_files(self, test_file):
        if not Reason.objects.filter(id=1200):
            reason = Reason(id=1200)
            reason.save()
        origin_record = self.create_record_card()
        RecordFile.objects.create(record_card=origin_record, file=test_file.name, filename=test_file.name)
        destination_record = self.create_record_card()
        storage = Mock(spec=DummyStorage)
        with patch("main.storage.imi_minio_storage.IMIMinioMediaStorage", storage):
            files = CopyMinioFiles(origin_record, destination_record, origin_record.responsible_profile).copy_files()
            for record_file in files:
                assert test_file.name in record_file.filename
                assert record_file.record_card == destination_record

    def test_get_new_file_name(self):
        original_file_name = "test.txt"
        new_file_name = CopyMinioFiles.get_new_file_name(original_file_name)
        assert "-" in new_file_name
        assert original_file_name in new_file_name
        assert len(new_file_name.split("-{}".format(original_file_name))[0]) == CopyMinioFiles.uuid_length

    def test_save_db_copy(self, test_file):
        if not Reason.objects.filter(id=1200):
            reason = Reason(id=1200)
            reason.save()
        record = self.create_record_card()
        storage = Mock(spec=DummyStorage)
        with patch("main.storage.imi_minio_storage.IMIMinioMediaStorage", storage):
            record_file = CopyMinioFiles(record, record, record.responsible_profile).save_db_copy(
                test_file.name, test_file.name, test_file.name)
            assert record_file.filename == test_file.name
            assert record_file.file == test_file
            assert record_file.record_card == record
            assert Comment.objects.get(record_card=record, reason_id=Reason.RECORDFILE_COPIED)
