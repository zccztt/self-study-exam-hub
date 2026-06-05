# -*- coding: utf-8 -*-
"""
Elasticsearch 客户端管理
"""

from elasticsearch import Elasticsearch, AsyncElasticsearch
from backend.config import settings
from typing import Dict, List, Optional


class ElasticsearchClient:
    """Elasticsearch 客户端类"""

    def __init__(self):
        self.client = Elasticsearch([settings.ELASTICSEARCH_URL])
        self.async_client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])

    def create_index(self, index_name: str, mappings: Dict) -> bool:
        """创建索引"""
        try:
            if not self.client.indices.exists(index=index_name):
                self.client.indices.create(index=index_name, body=mappings)
                return True
            return False
        except Exception as e:
            print(f"Create index error: {e}")
            return False

    def index_document(self, index_name: str, doc_id: str, document: Dict) -> bool:
        """索引文档"""
        try:
            self.client.index(index=index_name, id=doc_id, body=document)
            return True
        except Exception as e:
            print(f"Index document error: {e}")
            return False

    def bulk_index(self, index_name: str, documents: List[Dict]) -> bool:
        """批量索引文档"""
        try:
            from elasticsearch.helpers import bulk
            actions = [
                {
                    "_index": index_name,
                    "_id": doc.get('id'),
                    "_source": doc
                }
                for doc in documents
            ]
            bulk(self.client, actions)
            return True
        except Exception as e:
            print(f"Bulk index error: {e}")
            return False

    def search(
        self,
        index_name: str,
        query: Dict,
        from_: int = 0,
        size: int = 20
    ) -> Dict:
        """搜索文档"""
        try:
            response = self.client.search(
                index=index_name,
                body=query,
                from_=from_,
                size=size
            )
            return response
        except Exception as e:
            print(f"Search error: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}}

    def delete_document(self, index_name: str, doc_id: str) -> bool:
        """删除文档"""
        try:
            self.client.delete(index=index_name, id=doc_id)
            return True
        except Exception as e:
            print(f"Delete document error: {e}")
            return False

    async def async_search(
        self,
        index_name: str,
        query: Dict,
        from_: int = 0,
        size: int = 20
    ) -> Dict:
        """异步搜索文档"""
        try:
            response = await self.async_client.search(
                index=index_name,
                body=query,
                from_=from_,
                size=size
            )
            return response
        except Exception as e:
            print(f"Async search error: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}}


# 全局 Elasticsearch 客户端实例
es_client = ElasticsearchClient()

# 题目索引映射
QUESTION_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "subject_id": {"type": "integer"},
            "subject_name": {"type": "keyword"},
            "content": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart"
            },
            "type": {"type": "keyword"},
            "answer": {"type": "keyword"},
            "explanation": {
                "type": "text",
                "analyzer": "ik_max_word"
            },
            "year": {"type": "integer"},
            "month": {"type": "integer"},
            "chapter_id": {"type": "integer"},
            "chapter_name": {"type": "keyword"},
            "difficulty": {"type": "keyword"},
            "frequency": {"type": "integer"},
            "knowledge_points": {"type": "keyword"},
        }
    }
}
