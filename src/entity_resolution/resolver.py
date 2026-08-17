import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz


@dataclass
class ResolutionResult:
    raw_name: str
    canonical_name: str
    confidence: float
    matched: bool


class EntityResolver:
    def __init__(
        self,
        seed_entities: dict[str, list[str]] | None = None,
        threshold: int = 88,
    ):
        self.threshold = threshold

        self.seed_entities = seed_entities or {
            "OpenAI": [
                "openai",
                "open ai",
                "openai inc",
                "openai, inc.",
            ],
            "Google DeepMind": [
                "google deepmind",
                "deepmind",
                "google-deepmind",
            ],
            "Anthropic": [
                "anthropic",
                "anthropic ai",
                "anthropic pbc",
            ],
            "Meta AI": [
                "meta ai",
                "meta artificial intelligence",
                "facebook ai",
            ],
            "Microsoft": [
                "microsoft",
                "microsoft corporation",
                "msft",
            ],
        }

    @staticmethod
    def normalize(value: str) -> str:
        value = unicodedata.normalize(
            "NFKD",
            value,
        )

        value = value.lower()

        value = re.sub(
            r"[^\w\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    def resolve(
        self,
        raw_name: str,
    ) -> ResolutionResult:

        normalized = self.normalize(
            raw_name
        )

        best_name = raw_name
        best_score = 0

        for canonical, aliases in self.seed_entities.items():

            candidates = [
                canonical,
                *aliases,
            ]

            for candidate in candidates:

                score = fuzz.ratio(
                    normalized,
                    self.normalize(candidate),
                )

                if score > best_score:
                    best_score = score
                    best_name = canonical

        if best_score >= self.threshold:

            return ResolutionResult(
                raw_name=raw_name,
                canonical_name=best_name,
                confidence=best_score / 100,
                matched=True,
            )

        return ResolutionResult(
            raw_name=raw_name,
            canonical_name=raw_name,
            confidence=best_score / 100,
            matched=False,
        )