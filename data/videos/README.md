# 视频元数据目录

此目录用于存放视频资源元数据。

## 数据格式

```json
[
  {
    "id": 1,
    "title": "马克思主义基本原理 - 第三章 唯物辩证法",
    "url": "https://www.bilibili.com/video/BV1xx411c7kX",
    "source": "bilibili",
    "duration": 2720,
    "author": "XX教育",
    "view_count": 123000,
    "publish_date": "2023-09-15",
    "subject_id": 1,
    "subject_name": "马克思主义基本原理概论",
    "chapter_id": 3,
    "chapter_name": "第三章 世界的联系、发展及其规律",
    "knowledge_points": ["矛盾的普遍性与特殊性", "对立统一规律"],
    "related_question_ids": [45, 78, 123, 234],
    "tags": ["重点章节", "高频考点"]
  }
]
```

## 支持的视频来源

- `bilibili`: B站
- `netease`: 网易公开课
- `tencent`: 腾讯课堂
- `youtube`: YouTube
- `custom`: 自建上传

## 导入命令

```bash
python scripts/data_import.py --type videos --source data/videos/videos.json
```
