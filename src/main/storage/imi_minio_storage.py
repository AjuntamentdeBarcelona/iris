from urllib.parse import urlparse

import minio
from django.utils.functional import cached_property

from minio.helpers import get_target_url
from minio_storage.storage import MinioMediaStorage, get_setting
from django.conf import settings


def create_minio_media_client_from_settings(default_region=None):
    """
    Sin files are uploaded in the internal ICP network, we need a different client for signing and accessing the
    different files. This is a special case for IMI architecture.
    :return: Minio client for accessing media file.s.
    :rtype: minio.Minio
    """
    endpoint = get_setting("MINIO_MEDIA_URL")
    access_key = get_setting("MINIO_STORAGE_ACCESS_KEY")
    secret_key = get_setting("MINIO_STORAGE_SECRET_KEY")
    secure = get_setting("MINIO_MEDIA_URL_SECURE", True)
    region = get_setting("MINIO_STORAGE_REGION", default_region)
    client = minio.Minio(endpoint,
                         access_key=access_key,
                         secret_key=secret_key,
                         secure=secure,
                         region=region)
    return client


class IMIMinioMediaStorage(MinioMediaStorage):
    DEFAULT_IRIS1_BUCKET = 'iris1'

    @cached_property
    def media_client(self):
        return create_minio_media_client_from_settings(default_region=self.client._get_bucket_region(self.bucket_name))

    @property
    def iris1_bucket(self):
        return getattr(settings, 'MINIO_STORAGE_IRIS1_MEDIA_BUCKET_NAME', self.DEFAULT_IRIS1_BUCKET)

    def get_url_bucket(self, name):
        """
        IRIS1 files are placed on the root path, which is considered an special folder not usable in IRIS2.
        :return: Bucket for the url, IRIS1 files are placed on a different bucket due to IMI requirements.
        """
        parts = name.split('/')
        return self.bucket_name if len(parts) > 1 and parts[0].strip() else self.iris1_bucket

    def url(self, name):
        # type: (str) -> str

        # NOTE: Here be dragons, when a external base_url is used the code
        # below is both using "internal" minio clint APIs and somewhat
        # subverting how minio/S3 expects urls to be generated in the first
        # place.
        bucket_name = self.get_url_bucket(name)
        # PUBLIC URL GENERATION: Adjust base url to the selected bucket
        base_url = self.base_url.replace(self.bucket_name, bucket_name)
        if self.presign_urls:
            url = self.media_client.presigned_get_object(bucket_name, name.lstrip('/'))
            if self.base_url is not None:
                parsed_url = urlparse(url)
                path = parsed_url.path.split(bucket_name, 1)[1]
                url = '{0}{1}?{2}{3}{4}'.format(
                    base_url, path, parsed_url.params,
                    parsed_url.query, parsed_url.fragment)

        else:
            if self.base_url is not None:
                def strip_beg(path):
                    while path.startswith('/'):
                        path = path[1:]
                    return path

                def strip_end(path):
                    while path.endswith('/'):
                        path = path[:-1]
                    return path

                url = "{}/{}".format(strip_end(base_url),
                                     strip_beg(name))
            else:
                url = get_target_url(self.client._endpoint_url,
                                     bucket_name=bucket_name,
                                     object_name=name,
                                     )
        if get_setting("MINIO_STORAGE_MEDIA_HIDE_DOMAIN"):
            url = url.split(get_setting("MINIO_MEDIA_URL"))[-1]
        return url


def get_minio_connection_info():
    """
    :return: minio bucket and minio client
    """
    minio_storage = IMIMinioMediaStorage()
    return minio_storage.bucket_name, minio_storage.media_client
