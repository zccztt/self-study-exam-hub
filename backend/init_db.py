# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建所有表结构
"""

from backend.database import engine
from backend.models import Base
from backend.elasticsearch_client import es_client, QUESTION_INDEX_MAPPING


def init_database():
    """初始化数据库"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def init_elasticsearch():
    """初始化 Elasticsearch 索引"""
    print("Creating Elasticsearch indices...")

    # 创建题目索引
    es_client.create_index("questions", QUESTION_INDEX_MAPPING)

    print("Elasticsearch indices created successfully!")


if __name__ == "__main__":
    print("=" * 50)
    print("Initializing Self-Study Exam Hub Database")
    print("=" * 50)

    try:
        init_database()
        init_elasticsearch()
        print("\n✅ All initialization completed successfully!")
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        raise
