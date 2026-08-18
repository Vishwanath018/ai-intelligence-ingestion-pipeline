from src.news.collector import NewsCollector


def make_record(
    url="https://example.com/article",
    title="Artificial Intelligence News",
):
    return {
        "schemaVersion": "1.0",
        "recordType": "NEWS",
        "source": {
            "name": "Example",
            "url": url,
        },
        "content": {
            "title": title,
            "date": "2026-08-18T12:00:00+00:00",
            "text": "Example article content",
            "url": url,
        },
        "collectedAt": "2026-08-18T12:00:00+00:00",
    }


def test_valid_news_records():
    collector = NewsCollector()

    records = [
        make_record(
            "https://example.com/1",
            "AI article one",
        ),
        make_record(
            "https://example.com/2",
            "AI article two",
        ),
    ]

    assert collector.validate(records) is True


def test_duplicate_news_urls_are_rejected():
    collector = NewsCollector()

    records = [
        make_record(
            "https://example.com/1",
            "AI article one",
        ),
        make_record(
            "https://example.com/1",
            "AI article duplicate",
        ),
    ]

    assert collector.validate(records) is False


def test_invalid_news_record_is_rejected():
    collector = NewsCollector()

    records = [
        make_record(
            "",
            "Article without URL",
        )
    ]

    assert collector.validate(records) is False


def test_empty_news_title_is_rejected():
    collector = NewsCollector()

    records = [
        make_record(
            "https://example.com/1",
            "",
        )
    ]

    assert collector.validate(records) is False
