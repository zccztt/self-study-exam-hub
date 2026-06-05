# 题库数据目录

此目录用于存放题库数据文件。

## 数据格式

### JSON 格式示例

```json
[
  {
    "id": 1,
    "subject_id": 1,
    "subject_name": "马克思主义基本原理概论",
    "content": "物质和意识的关系是...",
    "type": "single_choice",
    "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
    "answer": "A",
    "explanation": "答案解析内容...",
    "year": 2023,
    "month": 10,
    "chapter_id": 2,
    "chapter_name": "第二章 世界的物质性及发展规律",
    "difficulty": "medium",
    "frequency": 3,
    "knowledge_points": ["物质与意识", "辩证唯物主义"]
  }
]
```

### CSV 格式示例

```csv
id,subject_id,subject_name,content,type,options,answer,explanation,year,month,chapter_id,chapter_name,difficulty,frequency,knowledge_points
1,1,马克思主义基本原理概论,物质和意识的关系是...,single_choice,"A. 选项1|B. 选项2|C. 选项3|D. 选项4",A,答案解析内容...,2023,10,2,第二章 世界的物质性及发展规律,medium,3,"物质与意识,辩证唯物主义"
```

## 导入命令

```bash
# 导入JSON格式题库
python scripts/data_import.py --type questions --source data/questions/2023_questions.json

# 导入CSV格式题库
python scripts/data_import.py --type questions --source data/questions/2023_questions.csv
```
