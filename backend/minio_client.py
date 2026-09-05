# -*- coding: utf-8 -*-
"""
MinIO 客户端管理
"""

import io
import logging
from typing import Optional

from minio import Minio

from backend.config import settings

logger = logging.getLogger(__name__)


class MinIOClient:
    """​MinIO 客户端类"""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,  # 开发环境使用 HTTP
        )
        self._available: bool = self._ensure_bucket_exists()

    @property
    def is_available(self) -> bool:
        return self._available

    def _ensure_bucket_exists(self) -> bool:
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET_NAME):
                self.client.make_bucket(settings.MINIO_BUCKET_NAME)
            return True
        except Exception as e:
            logger.error("Ensure bucket error: %s", e)
            return False

    def upload_file(self, object_name: str, file_data: bytes, content_type: str = 'application/octet-stream') -> bool:
        """上传文件"""
        if not self._available:
            logger.warning("MinIO unavailable, skipping upload for %s", object_name)
            return False
        try:
            file_stream = io.BytesIO(file_data)
            self.client.put_object(
                settings.MINIO_BUCKET_NAME,
                object_name,
                file_stream,
                length=len(file_data),
                content_type=content_type,
            )
            return True
        except Exception as e:
            logger.error("Upload file error: %s", e)
            return False

    def download_file(self, object_name: str) -> Optional[bytes]:
        """下载文件"""
        if not self._available:
            logger.warning("MinIO unavailable, skipping download for %s", object_name)
            return None
        try:
            response = self.client.get_object(settings.MINIO_BUCKET_NAME, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error("Download file error: %s", e)
            return None

    def delete_file(self, object_name: str) -> bool:
        """删除文件"""
        if not self._available:
            logger.warning("MinIO unavailable, skipping delete for %s", object_name)
            return False
        try:
            self.client.remove_object(settings.MINIO_BUCKET_NAME, object_name)
            return True
        except Exception as e:
            logger.error("Delete file error: %s", e)
            return False

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """获取预签名URL"""
        if not self._available:
            logger.warning("MinIO unavailable, skipping presigned URL for %s", object_name)
            return None
        try:
            url = self.client.presigned_get_object(
                settings.MINIO_BUCKET_NAME,
                object_name,
                expires=expires,
            )
            return url
        except Exception as e:
            logger.error("Get presigned URL error: %s", e)
            return None

    def list_files(self, prefix: str = '') -> list:
        """列出文件"""
        if not self._available:
            logger.warning("MinIO unavailable, skipping list_files")
            return []
        try:
            objects = self.client.list_objects(
                settings.MINIO_BUCKET_NAME,
                prefix=prefix,
                recursive=True,
            )
            return [obj.object_name for obj in objects]
        except Exception as e:
            logger.error("List files error: %s", e)
            return []


# 全局 MinIO 客户端实例
minio_client = MinIOClient()
