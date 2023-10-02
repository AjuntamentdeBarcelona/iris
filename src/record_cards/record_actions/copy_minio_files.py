import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import Reason
from main.storage.imi_minio_storage import get_minio_connection_info
from record_cards.models import RecordFile, record_files_path, Comment


class CopyMinioFiles:
    """
    Class to cppu the files from a record card to another, on minio storage
    """

    uuid_length = 13

    def __init__(self, origin_record, destination_record, group) -> None:
        super().__init__()
        self.origin_record = origin_record
        self.destination_record = destination_record
        self.group = group
        self.minio_bucket, self.minio_client = get_minio_connection_info()

    def copy_files(self):
        return [self.copy_file(record_file) for record_file in self.origin_record.recordfile_set.all()]

    def copy_file(self, record_file):
        original_filename = record_file.filename
        new_file_name = self.get_new_file_name(original_filename)
        new_file_path = record_files_path(None, new_file_name)
        with transaction.atomic():
            db_file = self.save_db_copy(new_file_path, new_file_name, original_filename)
            try:
                self.copy_on_minio(new_file_path, record_file.file.name)
            except:  # noqa
                default_storage.save(new_file_path, record_file.file)
            return db_file

    def copy_on_minio(self, new_file_path, original_filename):
        origin_file_path = "{}/{}".format(self.minio_bucket, original_filename)
        self.minio_client.copy_object(self.minio_bucket, new_file_path, origin_file_path)

    @staticmethod
    def get_new_file_name(original_filename):
        return "{}-{}".format(str(uuid.uuid4())[:CopyMinioFiles.uuid_length], original_filename)

    def save_db_copy(self, new_file_path, new_file_name, original_filename):
        record_file = RecordFile.objects.create(record_card=self.destination_record, file=new_file_path,
                                                filename=new_file_name)
        comment = _("File {} was copied from record {}").format(original_filename,
                                                                self.origin_record.normalized_record_id)
        Comment.objects.create(record_card=self.destination_record, reason_id=Reason.RECORDFILE_COPIED,
                               group=self.group, comment=comment)
        return record_file
