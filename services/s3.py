import os
import shutil
import tempfile
from typing import Optional

import boto3
from botocore.config import Config


def get_s3_client():
    region = os.getenv("AWS_REGION")
    bucket = os.getenv("AWS_S3_BUCKET")
    if not region or not bucket:
        return None
    return boto3.client("s3", config=Config(region_name=region))


def download_s3_key_to_path(key: str, dest_path: str) -> None:
    s3 = get_s3_client()
    if s3 is None:
        raise RuntimeError("S3 is not configured")
    bucket = os.getenv("AWS_S3_BUCKET")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        s3.download_file(bucket, key, tmp_path)
        with open(dest_path, "wb") as f_out, open(tmp_path, "rb") as f_in:
            shutil.copyfileobj(f_in, f_out)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def upload_path_to_s3_key(src_path: str, key: str) -> None:
    s3 = get_s3_client()
    if s3 is None:
        raise RuntimeError("S3 is not configured")
    bucket = os.getenv("AWS_S3_BUCKET")
    s3.upload_file(src_path, bucket, key)


