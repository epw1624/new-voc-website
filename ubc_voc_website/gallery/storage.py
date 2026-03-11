import os
from storages.backends.s3boto3 import S3Boto3Storage

class LegacyGalleryStorage(S3Boto3Storage):
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    bucket_name = os.getenv("GALLERY_S3_BUCKET_NAME")
    region_name = os.getenv("AWS_REGION_NAME")

    default_acl = "private"
    querystring_auth = True
    querystring_expire = 3600
    file_overwrite = False
    custom_domain = False