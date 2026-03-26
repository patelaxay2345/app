import os
import re
import logging
import httpx
from urllib.parse import urlparse, unquote
from typing import Optional, Dict, Any, Tuple, Generator

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from services.encryption import EncryptionService

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, encryption_service: EncryptionService):
        self.encryption_service = encryption_service

    def _parse_s3_url(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse bucket and key from an S3 HTTPS URL.

        Supports:
          - https://bucket.s3.region.amazonaws.com/key
          - https://bucket.s3.amazonaws.com/key
          - https://s3.region.amazonaws.com/bucket/key
          - https://s3.amazonaws.com/bucket/key
        """
        parsed = urlparse(url)
        host = parsed.hostname or ""
        path = unquote(parsed.path).lstrip("/")

        # Format: bucket.s3[.region].amazonaws.com/key
        match = re.match(r"^(.+)\.s3[.\w-]*\.amazonaws\.com$", host)
        if match:
            return match.group(1), path

        # Format: s3[.region].amazonaws.com/bucket/key
        match = re.match(r"^s3[.\w-]*\.amazonaws\.com$", host)
        if match and "/" in path:
            bucket, _, key = path.partition("/")
            return bucket, key

        logger.warning(f"[S3] Could not parse S3 URL: {url}")
        return None, None

    def _resolve_bucket_key(
        self, recording_url: str, config_bucket: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Resolve bucket, key, and optional custom endpoint from a recording URL.

        Tries AWS-style URL parsing first, then falls back to path-style
        parsing for non-AWS S3-compatible storage (e.g., Linode Object Storage).

        Returns (bucket, key, endpoint_url).
        """
        bucket, key = self._parse_s3_url(recording_url)
        if bucket and key:
            return bucket, key, None

        # Path-style parsing for non-AWS S3 (matches playAudioFile in Node.js)
        parsed = urlparse(recording_url)
        hostname = parsed.hostname or ""
        pathname = unquote(parsed.path)
        path_parts = [p for p in pathname.split("/") if p]

        if len(path_parts) >= 2:
            return path_parts[0], "/".join(path_parts[1:]), f"{parsed.scheme}://{hostname}"

        if config_bucket:
            return config_bucket, parsed.path.lstrip("/"), None

        return None, None, None

    @staticmethod
    def _is_public_url(hostname: str) -> bool:
        """Match isPublicUrl from Node.js helper — amazonaws.com = public."""
        return "amazonaws.com" in hostname

    def _detect_content_type(self, key: str, fallback: str = "audio/mpeg") -> str:
        """Detect audio content type from file extension."""
        ext = os.path.splitext(key)[1].lower()
        ext_map = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".flac": "audio/flac",
            ".webm": "audio/webm",
            ".aac": "audio/aac",
        }
        return ext_map.get(ext, fallback)

    def get_playable_url(
        self, s3_config: dict, recording_url: str, expiry: int = 3600
    ) -> Dict[str, Any]:
        """
        Return a URL the browser can play directly in an <audio> element.

        Two paths (mirrors playAudioFile logic from Node.js app_api):
          1. Public URLs (amazonaws.com) — returned as-is, no credentials needed.
          2. Private S3-compatible storage (Linode, etc.) — a time-limited
             presigned URL is generated using the partner's credentials with
             the correct endpoint so the browser fetches directly from S3.

        The browser's native <audio> handles range requests, buffering, and
        seek — no file-size limit and zero server memory overhead.
        """
        parsed = urlparse(recording_url)
        hostname = parsed.hostname or ""

        # ── Public URL (amazonaws.com) — usable as-is ──
        if self._is_public_url(hostname):
            content_type = self._detect_content_type(recording_url)
            logger.info(f"[S3] Public URL, returning as-is: {recording_url[:120]}")
            return {"presignedUrl": recording_url, "contentType": content_type}

        # ── Private S3 (Linode, etc.) — generate presigned URL ──
        access_key = self.encryption_service.decrypt(s3_config.get("accessKeyId", ""))
        secret_key = self.encryption_service.decrypt(s3_config.get("secretAccessKey", ""))
        region = s3_config.get("region", "us-east-1")
        config_bucket = s3_config.get("bucket")

        if not access_key or not secret_key:
            logger.error("[S3] Missing decrypted credentials")
            return {"error": "Missing AWS credentials after decryption"}

        bucket, key, endpoint_url = self._resolve_bucket_key(recording_url, config_bucket)
        if not bucket or not key:
            return {"error": f"Cannot parse bucket/key from URL: {recording_url[:100]}"}

        logger.info(
            f"[S3] Private S3: bucket={bucket}, key={key}, "
            f"endpoint={endpoint_url}, region={region}"
        )

        content_type = self._detect_content_type(key)

        boto_config = BotoConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            signature_version="s3v4",
        )
        if endpoint_url:
            boto_config = boto_config.merge(
                BotoConfig(s3={"addressing_style": "path"})
            )

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                endpoint_url=endpoint_url,
                config=boto_config,
            )

            presigned = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ResponseContentType": content_type,
                },
                ExpiresIn=expiry,
            )
            logger.info(f"[S3] Presigned URL generated for private S3")
            return {"presignedUrl": presigned, "contentType": content_type}

        except ClientError as e:
            logger.error(f"[S3] Failed to generate presigned URL: {e}")
            return {"error": f"S3 client error: {str(e)}"}

    def generate_presigned_url(
        self,
        s3_config: dict,
        recording_url: str,
        expiry: int = 3600,
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for a private S3 object.
        Returns dict with presignedUrl and debug info.
        """
        if not s3_config or not s3_config.get("enabled"):
            return {"error": "S3 not enabled"}

        access_key = self.encryption_service.decrypt(s3_config.get("accessKeyId", ""))
        secret_key = self.encryption_service.decrypt(s3_config.get("secretAccessKey", ""))
        region = s3_config.get("region", "us-east-1")
        config_bucket = s3_config.get("bucket")

        if not access_key or not secret_key:
            logger.error("[S3] Missing decrypted AWS credentials")
            return {"error": "Missing AWS credentials after decryption"}

        logger.info(f"[S3] Decrypted access_key starts with: {access_key[:4]}...")

        bucket, key = self._parse_s3_url(recording_url)
        logger.info(f"[S3] Parsed URL: bucket={bucket}, key={key}, input={recording_url[:120]}")
        if not bucket or not key:
            if config_bucket:
                bucket = config_bucket
                key = urlparse(recording_url).path.lstrip("/")
            else:
                return {"error": f"Cannot parse bucket/key from URL: {recording_url[:100]}"}

        # Detect content type from file extension
        ext = os.path.splitext(key)[1].lower()
        content_type_map = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".flac": "audio/flac",
            ".webm": "audio/webm",
            ".aac": "audio/aac",
        }
        content_type = content_type_map.get(ext, "audio/mpeg")
        logger.info(f"[S3] bucket={bucket}, key={key}, ext='{ext}', content_type={content_type}, region={region}")

        try:
            client = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )

            # First: HEAD the object to verify it exists and get its actual content type
            try:
                head = client.head_object(Bucket=bucket, Key=key)
                actual_ct = head.get("ContentType", "unknown")
                size = head.get("ContentLength", 0)
                logger.info(f"[S3] HEAD success: ContentType={actual_ct}, Size={size} bytes")
                # Use the actual content type from S3 if it's audio
                if actual_ct.startswith("audio/"):
                    content_type = actual_ct
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_msg = e.response["Error"]["Message"]
                logger.error(f"[S3] HEAD failed: {error_code} - {error_msg}")
                return {
                    "error": f"S3 object not accessible: {error_code} - {error_msg}",
                    "bucket": bucket,
                    "key": key,
                }

            presigned = client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ResponseContentType": content_type,
                },
                ExpiresIn=expiry,
            )
            logger.info(f"[S3] Presigned URL generated successfully")
            return {"presignedUrl": presigned, "contentType": content_type}

        except ClientError as e:
            logger.error(f"[S3] Failed to generate presigned URL: {e}")
            return {"error": f"S3 client error: {str(e)}"}
