import json

import pytest

from src.main import IntelligenceIngestionPipeline


class FakeCollector:

    def __init__(self, records):
        self.records = records

    async def collect(self):
        return self.records

    def validate(self, records):
        return True


def make_record(
    record_type,
    name,
):
    return {
        "schemaVersion": "1.0",
        "recordType": record_type,
        "source": {
            "name": "Test Source",
            "url": "https://example.com",
        },
        "content": {
            "entityName": name,
        },
    }


@pytest.mark.asyncio
async def test_pipeline_entity_resolution_and_storage(
    tmp_path,
    monkeypatch,
):

    pipeline = IntelligenceIngestionPipeline(
        max_results=1
    )

    pipeline.output.output_dir = tmp_path

    startup_record = make_record(
        "STARTUP",
        "Test Startup",
    )

    pipeline.results = {
        "startups": [
            startup_record
        ],
        "products": [],
        "research": [],
        "jobs": [],
        "news": [],
    }

    pipeline.status = {
        "startups": "SUCCESS",
        "products": "SUCCESS",
        "research": "SUCCESS",
        "jobs": "SUCCESS",
        "news": "SUCCESS",
    }

    pipeline.register_live_entities()

    mappings = (
        pipeline.resolve_entities()
    )

    assert len(mappings) == 1

    assert mappings[0][
        "raw_name"
    ] == "Test Startup"

    assert mappings[0][
        "canonical_name"
    ] == "Test Startup"

    assert mappings[0][
        "confidence"
    ] == 1.0

    assert mappings[0][
        "matched"
    ] is True

    pipeline.save_outputs()

    unified_path = (
        tmp_path
        / "unified_intelligence.json"
    )

    mapping_path = (
        tmp_path
        / "entity_mapping_log.json"
    )

    assert unified_path.exists()
    assert mapping_path.exists()

    with unified_path.open(
        encoding="utf-8"
    ) as file:
        unified = json.load(file)

    assert len(unified) == 1

    assert unified[0][
        "recordType"
    ] == "STARTUP"

    with mapping_path.open(
        encoding="utf-8"
    ) as file:
        mappings_saved = json.load(file)

    assert len(mappings_saved) == 1

    assert mappings_saved[0][
        "canonical_name"
    ] == "Test Startup"
