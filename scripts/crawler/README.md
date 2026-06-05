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

```python
# bilibili_crawler.py
# TODO: 实现B站视频元数据爬取
```

## 依赖

```bash
pip install beautifulsoup4 requests selenium
```
