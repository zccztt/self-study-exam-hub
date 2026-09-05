from backend.models.past_paper_source import PastPaperSource
from scripts.save_paper_sources import media_type
from backend.services.search_client import SearchResult


def test_media_type_classification() -> None:
    assert media_type(SearchResult("paper.pdf", "https://example.com/a.pdf", "")) == "pdf"
    assert media_type(SearchResult("试卷图片", "https://example.com/a", "")) == "image"
    assert media_type(SearchResult("讲解", "https://www.bilibili.com/video/BV1abc", "")) == "video"
    assert PastPaperSource.__tablename__ == "past_paper_sources"
