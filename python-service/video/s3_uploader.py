"""
S3 uploader for final video files.
Uploads to AWS S3 and returns a public URL.
"""

import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

load_dotenv()
LOGGER = logging.getLogger(__name__)


def _get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "ap-south-1"),
    )


def _get_bucket() -> str:
    bucket = os.getenv("AWS_S3_BUCKET", "").strip()
    if not bucket:
        raise ValueError("AWS_S3_BUCKET not set in environment")
    return bucket


def upload_video_to_s3(local_path: str, job_id: str) -> str | None:
    """
    Upload a video file to S3.
    
    Returns the public URL on success, or None on failure.
    The file is stored at: videos/{job_id}.mp4
    """
    file_path = Path(local_path)
    if not file_path.exists():
        LOGGER.error("Cannot upload — file not found: %s", local_path)
        return None

    s3_key = f"videos/{job_id}.mp4"
    size_mb = file_path.stat().st_size / (1024 * 1024)
    LOGGER.info("Uploading %.1f MB to S3: %s", size_mb, s3_key)

    try:
        bucket = _get_bucket()
        client = _get_s3_client()

        client.upload_file(
            local_path,
            bucket,
            s3_key,
            ExtraArgs={
                "ContentType": "video/mp4",
            },
        )

        # Construct the public URL
        region = os.getenv("AWS_REGION", "ap-south-1")
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        LOGGER.info("Upload complete: %s", url)
        return url

    except NoCredentialsError:
        LOGGER.error("AWS credentials not found — skipping S3 upload")
        return None
    except ClientError as exc:
        LOGGER.error("S3 upload failed: %s", exc)
        return None
    except ValueError as exc:
        LOGGER.error("S3 config error: %s", exc)
        return None
    except Exception as exc:
        LOGGER.exception("Unexpected S3 upload error: %s", exc)
        return None
