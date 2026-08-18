import json

from src.storage.output_manager import OutputManager


def sample_record(record_type):
    return {
        "schemaVersion": "1.0",
        "recordType": record_type,
        "source": {
            "name": "Test Source",
            "url": "https://example.com",
        },
        "content": {
            "name": "Test Record",
        },
    }


def test_save_all_outputs(tmp_path):

    manager = OutputManager(
        output_dir=str(tmp_path)
    )

    startups = [
        sample_record("STARTUP")
    ]

    products = [
        sample_record("PRODUCT")
    ]

    research = [
        sample_record("RESEARCH_PAPER")
    ]

    jobs = [
        sample_record("JOB")
    ]

    news = [
        sample_record("NEWS")
    ]

    entity_mapping = [
        {
            "raw_name": "Test Company",
            "canonical_name": "Test Company",
            "entity_type": "STARTUP",
            "confidence": 1.0,
            "source_url": "https://example.com",
            "matched": True,
        }
    ]

    paths = manager.save_all(
        startups=startups,
        products=products,
        research_papers=research,
        jobs=jobs,
        news=news,
        entity_mapping=entity_mapping,
    )

    expected_files = [
        "startups.json",
        "products.json",
        "research_papers.json",
        "jobs.json",
        "news.json",
        "entity_mapping_log.json",
        "unified_intelligence.json",
    ]

    for filename in expected_files:

        path = tmp_path / filename

        assert path.exists()
        assert path.is_file()

    with open(
        tmp_path / "unified_intelligence.json",
        encoding="utf-8",
    ) as file:

        unified = json.load(file)

    assert len(unified) == 5

    record_types = {
        record["recordType"]
        for record in unified
    }

    assert record_types == {
        "STARTUP",
        "PRODUCT",
        "RESEARCH_PAPER",
        "JOB",
        "NEWS",
    }

    assert paths["unified_intelligence"].exists()
