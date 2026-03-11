from django.conf import settings

from storages.backends.s3boto3 import S3Boto3Storage

class LegacyGalleryStorage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        kwargs.update({
            "access_key": settings.S3_ACCESS_KEY,
            "secret_key": settings.S3_SECRET_KEY,
            "bucket_name": settings.GALLERY_S3_BUCKET_NAME,
            "region_name": settings.AWS_REGION_NAME,
            "default_acl": "private",
            "querystring_auth": True,
            "querystring_expire": 3600,
            "file_overwrite": False,
            "custom_domain": False,
        })
        super().__init__(*args, **kwargs)