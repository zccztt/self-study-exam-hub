# 知识点库目录

此目录用于存放知识点结构数据。

## 数据格式

```json
{
  "subject_id": 1,
  "subject_name": "马克思主义基本原理概论",
  "chapters": [
    {
      "id": 1,
      "name": "第一章 马克思主义是关于无产阶级和人类解放的科学",
      "sections": [
        {
          "id": 1,
          "name": "1.1 马克思主义的创立和发展",
          "knowledge_points": [
            {
              "id": 1,
              "name": "马克思主义的产生",
              "description": "马克思主义产生的经济社会根源、思想渊源和实践基础",
              "importance": "medium"
            },
            {
              "id": 2,
              "name": "马克思主义的发展",
              "description": "马克思主义在实践中的丰富和发展",
              "importance": "low"
            }
          ]
        },
        {
          "id": 2,
          "name": "1.2 马克思主义的鲜明特征",
          "knowledge_points": [
            {
              "id": 3,
              "name": "科学性",
              "description": "马克思主义的科学性体现",
              "importance": "high"
            }
          ]
        }
      ]
    }
  ]
}
```

## 导入命令

```bash
python scripts/data_import.py --type knowledge --source data/knowledge_base/marx.json
```
