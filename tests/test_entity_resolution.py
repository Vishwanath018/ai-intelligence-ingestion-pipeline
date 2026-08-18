from src.entity_resolution.resolver import EntityResolver


def test_normalize_entity_name():
    resolver = EntityResolver()

    assert resolver.normalize("Open AI, Inc.") == "open ai inc"


def test_exact_live_entity_resolution():
    resolver = EntityResolver()

    resolver.register_entity("DoorDash")

    result = resolver.resolve("DoorDash")

    assert result.matched is True
    assert result.canonical_name == "DoorDash"
    assert result.confidence == 1.0


def test_alias_resolution():
    resolver = EntityResolver()

    result = resolver.resolve("open ai")

    assert result.matched is True
    assert result.canonical_name == "OpenAI"
    assert result.confidence == 1.0


def test_unknown_entity_is_not_falsely_matched():
    resolver = EntityResolver()

    result = resolver.resolve(
        "CompletelyUnknownCompanyXYZ"
    )

    assert result.matched is False
    assert result.canonical_name == (
        "CompletelyUnknownCompanyXYZ"
    )
def test_similar_company_names_are_not_falsely_merged():
    resolver = EntityResolver(
        seed_entities={
            "Deel": [],
            "DeepL": [],
        }
    )

    result = resolver.resolve("DeepL")

    assert result.matched is True
    assert result.canonical_name == "DeepL"

    result = resolver.resolve("Deel")

    assert result.matched is True
    assert result.canonical_name == "Deel"
