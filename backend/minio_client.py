# -*- coding: utf-8 -*-
"""
MinIO 客户端管理
"""

from minio import Minio
from backend.config import settings
from typing import Optional
import io


class MinIOClient:
    """MinIO 客户端类"""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,  # 开发环境使用 HTTP
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET_NAME):
                self.client.make_bucket(settings.MINIO_BUCKET_NAME)
        except Exception as e:
            print(f"Ensure bucket error: {e}")

    def upload_file(self, object_name: str, file_data: bytes, content_type: str = 'application/octet-stream') -> bool:
        """上传文件"""
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
            print(f"Upload file error: {e}")
            return False

    def download_file(self, object_name: str) -> Optional[bytes]:
        """下载文件"""
        try:
            response = self.client.get_object(settings.MINIO_BUCKET_NAME, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            print(f"Download file error: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """删除文件"""
        try:
            self.client.remove_object(settings.MINIO_BUCKET_NAME, object_name)
            return True
        except Exception as e:
            print(f"Delete file error: {e}")
            return False

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """获取预签名URL"""
        try:
            url = self.client.presigned_get_object(
                settings.MINIO_BUCKET_NAME,
                object_name,
                expires=expires,
            )
            return url
        except Exception as e:
            print(f"Get presigned URL error: {e}")
            return None

    def list_files(self, prefix: str = '') -> list:
        """列出文件"""
        try:
            objects = self.client.list_objects(
                settings.MINIO_BUCKET_NAME,
                prefix=prefix,
                recursive=True,
            )
            return [obj.object_name for obj in objects]
        except Exception as e:
            print(f"List files error: {e}")
            return []


# 全局 MinIO 客户端实例
minio_client = MinIOClient()
