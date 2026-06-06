# 爬虫脚本目录

此目录用于存放数据爬虫脚本。

## 脚本列表

- `bilibili_crawler.py`: B站视频元数据爬虫
- `question_crawler.py`: 题目数据爬虫
- `README.md`: 本文件

## 使用注意事项

1. **遵守robots.txt**: 爬取前检查目标网站的robots.txt
2. **控制频率**: 添加合理的延迟，避免对服务器造成压力
3. **数据清洗**: 爬取后需进行数据清洗和格式化
4. **版权问题**: 注意数据的版权和使用许可

## 示例

```bash
# 按关键词抓取前 2 页并导出为 data_import.py 可导入的 JSON
python scripts/crawler/bilibili_crawler.py \
  --keyword "自考 马克思主义 基本原理" \
  --pages 2 \
  --subject-id 1 \
  --chapter-id 2 \
  --knowledge-point "物质与意识的辩证关系" \
  --output data/videos/bilibili_videos.json

# 按 BV 号或视频链接抓取
python scripts/crawler/bilibili_crawler.py \
  --bvid BV1xx411c7kX \
  --subject-name "马克思主义基本原理概论" \
  --tag 高频考点

# 导入爬取结果
python scripts/data_import.py --type videos --source data/videos/bilibili_videos.json
```

## 依赖

```bash
pip install httpx
```
