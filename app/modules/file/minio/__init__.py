import os
import tempfile
from datetime import timedelta

from minio import Minio
from minio.error import ResponseError, BucketAlreadyOwnedByYou, BucketAlreadyExists

MINIO_HOST = os.getenv('MINIO_HOST', 'minio:9000')
MINIO_SECURE = os.getenv('MINIO_SECURE', "False") == "True"


def connect():
    return Minio(
        MINIO_HOST,
        access_key=os.environ.get("S3_ACCESS_KEY"),
        secret_key=os.environ.get("S3_SECRET_KEY"),
        secure=MINIO_SECURE)


def put_file(bucket, filename, data):
    minioClient = connect()

    try:
        minioClient.make_bucket(bucket)
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass
    except ResponseError as err:
        raise
    else:
        # Put an object 'pumaserver_debug.log' with contents from 'pumaserver_debug.log'.
        if "file_content" in data:
            data["file"] = tempfile.TemporaryFile()
            data["file"].write(data["file_content"])
            data["file"].seek(0)

        length = len(data["file"].read())
        data["file"].seek(0)
        try:
            minioClient.put_object(
                bucket_name=bucket,
                object_name=filename,
                content_type=data["content-type"],
                data=data["file"],
                length=length)
        except Exception as err:
            print(err)


def get_file(bucket, filename):
    minioClient = connect()
    return minioClient.get_object(bucket, filename)


def get_file_public(bucket, filename, minutes):
    minioClient = connect()
    return minioClient.presigned_get_object(bucket, filename, expires=timedelta(minutes=minutes))
