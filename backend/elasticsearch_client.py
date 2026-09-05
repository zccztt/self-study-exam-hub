# -*- coding: utf-8 -*-
"""Elasticsearch wrapper used as an optional accelerator."""

import logging
from typing import Dict, List

from elasticsearch import Elasticsearch

from backend.config import settings

logger = logging.getLogger(__name__)


QUESTION_INDEX = "questions"

QUESTION_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "subject_id": {"type": "integer"},
            "chapter_id": {"type": "integer"},
            "content": {"type": "text"},
            "answer": {"type": "text"},
            "explanation": {"type": "text"},
            "source": {"type": "text"},
            "question_type": {"type": "keyword"},
            "year": {"type": "integer"},
            "difficulty": {"type": "keyword"},
            "frequency": {"type": "integer"},
        }
    }
}


class ElasticsearchClient:
    def __init__(self) -> None:
        self.client = Elasticsearch([settings.ELASTICSEARCH_URL])
        self._available: bool = self._check_connection()

    @property
    def is_available(self) -> bool:
        return self._available

    def _check_connection(self) -> bool:
        try:
            return self.client.ping()
        except Exception as e:
            logger.warning("Elasticsearch ping failed: %s", e)
            return False

    def create_index(self, index_name: str, mappings: Dict) -> bool:
        try:
            if not self.client.indices.exists(index=index_name):
                self.client.indices.create(index=index_name, body=mappings)
                return True
            return False
        except Exception:
            return False

    def index_document(self, index_name: str, doc_id: str, document: Dict) -> bool:
        try:
            self.client.index(index=index_name, id=doc_id, body=document)
            return True
        except Exception:
            return False

    def bulk_index(self, index_name: str, documents: List[Dict]) -> bool:
        try:
            from elasticsearch.helpers import bulk

            actions = [
                {"_index": index_name, "_id": document.get("id"), "_source": document}
                for document in documents
            ]
            bulk(self.client, actions)
            return True
        except Exception:
            return False

    def search_questions(self, keyword: str, page: int = 1, page_size: int = 20) -> Dict:
        if not self._available:
            logger.warning("Elasticsearch unavailable, skipping search for '%s'", keyword)
            return {"hits": {"total": {"value": 0}, "hits": []}}
        query = {
            "query": {
                "multi_match": {
                    "query": keyword,
                    "fields": ["content^2", "explanation", "answer"],
                    "fuzziness": "AUTO",
                }
            }
        }
        try:
            return self.client.search(
                index=QUESTION_INDEX,
                body=query,
                from_=(page - 1) * page_size,
                size=page_size,
            )
        except Exception:
            return {"hits": {"total": {"value": 0}, "hits": []}}


es_client = ElasticsearchClient()
