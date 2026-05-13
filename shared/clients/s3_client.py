"""Async S3 client wrapper.

Uses boto3 under the hood. When S3_ENDPOINT_URL is set (local dev / MinIO),
all calls are routed there; leaving it empty uses real AWS S3.
"""

import asyncio
from functools import partial

import boto3
from botocore.exceptions import ClientError


class S3Client:
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        kwargs: dict = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if aws_access_key_id:
            kwargs["aws_access_key_id"] = aws_access_key_id
            kwargs["aws_secret_access_key"] = aws_secret_access_key
        self._client = boto3.client("s3", **kwargs)

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        fn = partial(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        await asyncio.to_thread(fn)

    async def download(self, key: str) -> bytes:
        fn = partial(self._client.get_object, Bucket=self._bucket, Key=key)
        response = await asyncio.to_thread(fn)
        body = response["Body"]
        return await asyncio.to_thread(body.read)

    async def exists(self, key: str) -> bool:
        try:
            fn = partial(self._client.head_object, Bucket=self._bucket, Key=key)
            await asyncio.to_thread(fn)
            return True
        except ClientError:
            return False


def make_s3_client(
    bucket: str,
    region: str = "us-east-1",
    endpoint_url: str | None = None,
    minio_user: str | None = None,
    minio_password: str | None = None,
) -> S3Client:
    """Factory that reads MinIO creds when an endpoint URL is provided."""
    if endpoint_url and minio_user:
        return S3Client(bucket, region, endpoint_url, minio_user, minio_password)
    return S3Client(bucket, region, endpoint_url)
